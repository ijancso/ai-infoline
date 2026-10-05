# AI Infoline — Voice Turn Latency Report

Diagnosis only. No product code was changed; only opt-in instrumentation was added.

## 1. Pipeline (one conversational turn)

The active path uses Telnyx **Call Control + Media Streaming**. The `/telnyx/*` and
`/twilio/*` routers are legacy/unused for live turns.

```
Caller stops speaking
        │
        ▼ (Telnyx sends inbound_track mulaw 8kHz frames on WS)
Deepgram WS (nova-3, hu, endpointing=500ms, interim_results=false, smart_format)
        │  ── silence-hold 500ms then is_final ──
        ▼
routers/callcontrol.py::stream_ws  (WS receiver loop, lines 106-189)
        │  transcript captured at line 145-148
        ▼
routers/callcontrol.py::_respond   (lines 199-249)
        │
        ├── DB open session                    (AsyncSessionLocal, db.py:6-7)
        ├── services/call_service.upsert_call  (SELECT + UPDATE + COMMIT + REFRESH; call_service.py:20-41)
        ├── redundant SELECT for call.id       (callcontrol.py:229-231)  ← wastes one DB RTT
        ▼
services/claude_service.get_streaming_tts_token  (claude_service.py:147-227)
        │  system=[{cache_control: ephemeral}], model=claude-haiku-4-5-20251001, max_tokens=80
        ├── stream Claude tokens
        ├── on first "[.!?]" boundary → launch Google TTS  (asyncio.create_task, line 200)
        ├── break Claude stream
        ├── await _save_turn_to_db  (2 inserts + COMMIT; claude_service.py:60-70)
        ├── await tts_task
        ▼
services/tts_service.tts_token → _generate_audio  (tts_service.py:18-48)
        │  Google Cloud TTS (hu-HU-Wavenet-A, MP3), NEW httpx.AsyncClient per call
        │  bytes stored in-process _audio_store, keyed by URL-safe token
        ▼
services/callcontrol_service.play_audio → _post  (callcontrol_service.py:22-45)
        │  HTTP POST to Telnyx /actions/playback_start with audio_url = https://infoline.dev/telnyx/audio/{token}
        │  NEW httpx.AsyncClient per call, no connection reuse
        ▼
Telnyx fetches the MP3 via routers/telnyx_webhook.py::audio  (telnyx_webhook.py:47-53)
        │  extra hop: Telnyx GET → our server → Telnyx decodes MP3 → plays to caller
        ▼
Caller hears AI reply
```

Stage locations:

| # | Stage | File:function |
|---|---|---|
| 1 | End-of-speech (silence hold) | Deepgram, driven by `endpointing=500` in `callcontrol.py:126` |
| 2 | STT final delivered | `callcontrol.py:139-148 _recv_dg` |
| 3 | DB upsert + id fetch | `callcontrol.py:221-232` + `call_service.py:20-41` |
| 4 | LLM streaming | `claude_service.py:180-192` |
| 5 | TTS synth | `tts_service.py:34-48` |
| 6 | Save turn to DB | `claude_service.py:60-70` (awaited before `tts_task`) |
| 7 | Playback command → Telnyx | `callcontrol_service.py:41-45` + `_post` at :22-34 |
| 8 | Telnyx audio fetch | `telnyx_webhook.py:47-53` (Telnyx pulls, out of our clock) |

## 2. Stage table — evidence and rough numbers

Deployment reality confirmed by hostname `ubuntu-s-2vcpu-4gb-120gb-intel-nyc1-01`:
the droplet is in **DigitalOcean NYC1**. Anthropic and Google TTS endpoints are US-East,
so the middle of the pipeline runs on short RTTs; Telnyx signalling and the Hungarian
caller side pay ~80–100 ms one-way EU↔US.

**Measured** column comes from `call_emulator.py` runs with `LATENCY_DEBUG=1`, executed
**on the production droplet itself** — so it accurately represents the LLM + TTS legs
that are also invoked from `_respond`. Stages the emulator can't reach (Deepgram, DB,
Telnyx signalling, Telnyx audio-fetch) remain estimates.

Two turns, no tenant system prompt (base SYSTEM_PROMPT only, ~577 chars):

| Turn | llm_request_sent → llm_first_token | llm_first_token → llm_done (1st sentence) | llm_done → tts_first_audio | Total (Claude+TTS) |
|---|---|---|---|---|
| 1 (cold) | 501 ms | 208 ms (50-char sentence) | 383 ms | **1146 ms** |
| 2 (warm) | 420 ms | 425 ms (57-char sentence) | 376 ms | **1222 ms** |

Full stage table:

| Stage | Streaming? | Est. ms | Measured (emu) | Evidence / notes |
|---|---|---|---|---|
| Deepgram silence-hold (endpointing) | n/a | **500** | — (emu can't test) | `endpointing=500` (callcontrol.py:126). Hard floor between real speech end and `is_final`. |
| Deepgram STT compute + WS deliver | streamed | 50–150 | — | Nova-3 is fast; small extra for Deepgram → droplet WS. |
| DB `upsert_call` (SELECT+UPDATE+COMMIT+REFRESH) | no | 30–120 | — | `call_service.py:20-41`. 4 statements to managed PG in same region. |
| Redundant `SELECT call` | no | 10–40 | — | `callcontrol.py:229-231`. The Call object was already returned by `upsert_call`. |
| Anthropic first-token (Haiku 4.5, ephemeral cache) | streamed | 250–500 | **420–501** | US-East → NYC1, ~50-60 ms base network. Rest is Anthropic-side. Warm-cache benefit only ~80 ms observed (small prompt in emu). |
| Anthropic first-sentence tokens | streamed | 200–500 | **208–425** | Varies with sentence length (~150 tok/s Haiku 4.5). |
| `_save_turn_to_db` (2 INSERT + COMMIT) | no | 20–80 | — | `claude_service.py:60-70`. **Awaited before `await tts_task`** on hot path — but in production it may overlap with TTS if TTS is still in flight (both awaited sequentially in code order today). |
| Google TTS (hu-HU-Wavenet-A MP3) | no | 250–500 | **376–383** | `_generate_audio` in `tts_service.py`, brand-new `httpx.AsyncClient` per call → fresh TLS handshake. Very consistent — TLS + Google synth combined. |
| Telnyx `playback_start` HTTP POST | no | 150–350 | — | `callcontrol_service._post`, new httpx client per call (fresh TLS). |
| Telnyx fetch of `/telnyx/audio/{token}` + start decode | no | 200–500 | — | Extra GET back to our droplet, then MP3 decode + jitter buffer. Not visible in server logs. |
| **Middle-of-pipeline (Claude + TTS) measured** | | 950–1300 | **~1.15–1.22 s** | Emu-measured on droplet. |
| **Full turn (adding endpointing + DB + Telnyx hops)** | | 2.4–3.7 s | (need real call for exact) | Measured middle + estimated edges. |

The user-reported **5–6 s** exceeds the sum-of-measured + estimated (~2.5–3.7 s).
The gap of ~1.5–3 s in a real call is almost certainly hiding in the parts the emulator
can't touch:

1. **Telnyx audio-fetch + buffering** — after `playback_start` returns 200, Telnyx has to
   GET `/telnyx/audio/{token}` from our droplet in NYC1, decode the MP3 into their media
   pipeline, and cross the EU media edge back to the caller. Rough guess: 500–1500 ms.
2. **Deepgram end-of-speech behavior** — with mulaw/8kHz Hungarian audio and
   `interim_results=false`, Deepgram may hold longer than 500 ms in practice.
3. **Real Telnyx signalling RTT** — EU caller → Telnyx edge → our droplet in NYC1 →
   Telnyx US-East signalling. Every `_post` pays ~200-300 ms round-trip TLS.
4. **First-turn cold path** — when the Anthropic connection is truly cold (no reused
   HTTP/2 stream), first-token can spike to 700–900 ms.

## 3. Top fixes, ranked by save / effort

**Re-ranking after measurement:** the biggest surprise is how consistent and *dominant*
the Anthropic first-token latency is (420–500 ms) and how large Google TTS is
(~380 ms). Both are fundamentally network-plus-vendor and the low-effort fixes barely
move them. The endpointing hold (500 ms) and the invisible Telnyx audio-fetch hop are
the two remaining big rocks. Because of this, fix ordering is unchanged, but the
expected savings are refined below.



### Fix 1 — Reuse a single `httpx.AsyncClient` for TTS and Telnyx (P0)
**Save:** ~150–400 ms per turn (eliminates ≥2 TLS handshakes).
**Effort:** ~1 h.
- Create a module-level `httpx.AsyncClient` for `services/tts_service.py` and `services/callcontrol_service.py`, initialized in FastAPI `lifespan` and closed on shutdown.
- Today: `tts_service.py:41` and `callcontrol_service.py:26` each do `async with httpx.AsyncClient(...) as client:` **per request**, opening a new TCP+TLS every call.
- Risks: none serious. Handle client lifecycle in the `lifespan` context manager (`main.py:40-48`). Keep connect timeout tight.

### Fix 2 — Drop `endpointing=500` to `endpointing=250` (or use `utterance_end_ms`) (P0)
**Save:** ~200–300 ms per turn.
**Effort:** 15 min + a real call to validate.
- File: `routers/callcontrol.py:126`.
- Risks: too-aggressive endpointing chops off users mid-sentence, producing broken transcripts and jumpy AI. Test with representative Hungarian speakers. If false-endpoints get worse, revert or try Deepgram `utterance_end_ms` (Deepgram-side smarter EOS) instead of raw endpointing.

### Fix 3 — Remove redundant DB SELECT and move `_save_turn_to_db` off the hot path (P1)
**Save:** ~40–150 ms per turn.
**Effort:** ~30 min.
- `callcontrol.py:229-231` re-selects the Call row after `upsert_call` already returned it. `upsert_call` returns `Call`; just use `call.id`.
- `claude_service.py:204-206` awaits `_save_turn_to_db` **before** `await tts_task`. Instead: launch it as a background task with `asyncio.create_task` and await it after `play_audio` (or fire-and-forget with error logging).
- Risks: if the process dies between play and save, that turn is lost. Acceptable for phone-call history that already has other observability (Telnyx side).

### Fix 4 — Serve TTS audio bytes directly to Telnyx (avoid the round-trip fetch) (P1)
**Save:** ~150–400 ms per turn (removes Telnyx→server GET + MP3 buffer).
**Effort:** 2–4 h (Telnyx docs review + change).
Options, ranked:
1. Use Telnyx `playback_start` with a data-URL / base64 payload, if supported for the account type — check Telnyx docs; some regions accept `audio_url: data:audio/mpeg;base64,...`.
2. Stream audio back over the already-open Media Stream WebSocket (`streaming_start` bidirectional). Requires switching TTS to a streaming vendor (e.g., Deepgram Aura, ElevenLabs streaming, or Google TTS Chirp streaming with LINEAR16 → mulaw resample) and writing outbound frames onto the same WS. Bigger refactor.
3. Serve audio from an edge CDN (DO Spaces + CDN) closer to Telnyx.
- Risks: (1) depends on Telnyx account limits — verify with a test call. (2) is a larger architecture change; only worth it if fixes 1–3 aren't enough. MP3 → mulaw resample must run in a threadpool.

### Fix 5 — Locate the droplet closer to Telnyx media / callers (P2)
**Save:** ~50–200 ms per turn (compounded across Deepgram WS, Anthropic HTTP, Telnyx HTTP).
**Effort:** infra migration — half a day.
- Terraform default is `nyc1` (`terraform/variables.tf:11`).
- If callers are Hungarian, move to `ams3` (Amsterdam) or `fra1` (Frankfurt). But Anthropic is US-only, so Anthropic RTT goes up. Net win depends on the mix (Deepgram + Telnyx sit both in EU and US POPs; Anthropic is US-East primarily). Measure first.
- Risks: managed PG cluster must be re-created in the new region (data migration). Redirect Telnyx numbers to new IP/domain.

### Fix 6 (bonus, low effort) — Trim / cache the system prompt (P2)
**Save:** 0–200 ms per turn on first-turn or after cache TTL.
**Effort:** ~30 min.
- `_build_prompt` (`claude_service.py:73-79`) concatenates `SYSTEM_PROMPT + tenant.system_prompt + tenant.knowledge_base`. If any tenant has a large knowledge base, first-turn Anthropic input tokens spike and cache-miss cost grows.
- Already uses `cache_control: ephemeral` (5-min TTL); consider a keep-alive ping (a cheap Anthropic call every 4 min per active session) to keep the cache warm. Or use larger cache tier if available.

## 4. How to measure — status and next step

**Done so far:** ran `LATENCY_DEBUG=1 python3 call_emulator.py --no-audio` on the
droplet with two Hungarian test prompts. Measurements are in §2. This covers the
middle of the pipeline (Anthropic + Google TTS) but not the phone-line-specific
stages (Deepgram, Telnyx signalling, Telnyx audio playback delivery).

**Still needed for a full picture:** one real phone call so we can see the STT,
Telnyx and DB stages. Instructions if you can place one:

`LATENCY_DEBUG=1` is already in `/home/jancso/ai-infoline/.env`; the api container was
rebuilt and recreated, so the instrumentation is active in production.

1. Call the live test number (**+1 440 644 4466**, US Telnyx). Note: since it's a US
   number your signalling RTT is *shorter* than a Hungarian caller experiences;
   add ~150–200 ms to the Telnyx-side numbers to project the EU-caller reality.
2. Ask a short question in Hungarian, wait for the reply, then hang up.
3. On the droplet:
   ```
   docker compose -f docker-compose.prod.yml logs --since 5m api | grep LATENCY
   ```
4. Paste the `LATENCY | …` lines back and I'll fill the phone-only stages in §2.

Each turn produces 8 lines: `speech_end_detected` (estimated as `stt_done - 500ms`),
`stt_done`, `db_ready`, `llm_request_sent`, `llm_first_token`, `llm_done`,
`tts_first_audio`, `audio_sent`. `audio_sent` = when the Telnyx POST returns; Telnyx-side
buffering adds another 200–500 ms invisible server-side.

## 5. What I changed in this session (removable)

Instrumentation only. No behaviour change when `LATENCY_DEBUG` is unset.

- **New file:** `api/services/latency_debug.py` — `TurnTimer` class + `new_timer()`. Reads `LATENCY_DEBUG` env once at import; `mark()` is a no-op unless enabled.
- **Modified:** `api/routers/callcontrol.py`
  - Added `stt_done_at: Optional[float]` local + capture inside `_recv_dg` (lines ~130, 140-148).
  - `_respond(...)` now accepts `stt_done_at`; creates a `TurnTimer` with `t0 = stt_done_at - 0.5s` and emits `speech_end_detected` + `stt_done` + `db_ready` + `audio_sent`.
- **Modified:** `api/services/claude_service.py`
  - `get_streaming_tts_token(...)` now accepts optional `timer` kwarg. Emits `llm_request_sent`, `llm_first_token`, `llm_done`, `tts_first_audio`. Auto-creates a timer when called from a non-router context (e.g. `call_emulator.py`) if `LATENCY_DEBUG=1`.
- **Env:** appended `LATENCY_DEBUG=1` to `/home/jancso/ai-infoline/.env`.
- **Deploy:** rebuilt and recreated only the `api` container via
  `docker compose -f docker-compose.prod.yml up -d --build api`. Postgres & frontend
  untouched.

### To remove instrumentation cleanly
1. `git rm api/services/latency_debug.py`
2. `git checkout HEAD -- api/routers/callcontrol.py api/services/claude_service.py`
   (or manually revert: remove `stt_done_at` capture, remove `timer` param, remove all `timer.mark(...)` calls and the auto-timer fallback).
3. Remove the `LATENCY_DEBUG=1` line from `.env`.
4. `docker compose -f docker-compose.prod.yml up -d --build api` to redeploy the clean image.

## 6. Open questions / things I did not verify

- ~~**Actual droplet region.**~~ Confirmed **NYC1** from hostname `ubuntu-s-2vcpu-4gb-120gb-intel-nyc1-01`.
- **Anthropic prompt-cache hit rate in production.** `Claude válasz | … cache_read=…` is already logged in `claude_service.py:131-138`; check recent logs to see if the cache is being read (`cache_read` > 0).
- **Deepgram false-endpoints today.** If callers already get cut off, the 500 ms endpointing is likely being pushed by real EOS behavior — don't reduce it without listening tests.
- **Telnyx SIP media region.** Telnyx auto-selects an edge; if calls are Hungarian we should have EU media. Verify in the Telnyx portal (Call Detail Records → media path).
- **Whether `playback_start` with base64 `audio_url` is supported on your Telnyx account.** Confirm before committing to fix #4 option 1.
