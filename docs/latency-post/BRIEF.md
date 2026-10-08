# Brief: "Cutting voice-agent latency" — LinkedIn post + public article

Owner: István. Written from the Claude mobile chat; executed by Claude Code CLI on the droplet.
Hand-off loop: CLI works from this file → commits + pushes → the chat pulls the repo and writes the final post.

## Goal

1. Actually reduce AI Infoline's per-turn latency (user-reported **5–6 s** today).
2. Publish a short article (this repo, `docs/latency-post/ARTICLE.md` + a web page) and a LinkedIn post linking to it.
3. **Every number must be traceable** to a commit and a row in `results.csv`. No invented or rounded-up numbers. Estimates are labelled as estimates.

## Hard rules for the CLI

- One optimization = one commit, prefix `perf(latency): <fix>`. Put the before/after median in the commit body.
- **Push after every commit** (and push WIP to a branch if stopping mid-step) — István follows progress and asks questions from the mobile chat, which only sees pushed code.
- Measure before AND after each fix with the same protocol (below). If a fix doesn't help, keep the commit + measurement anyway (or revert with a commit) — a "didn't work" row makes the article credible.
- Never commit secrets, `.env`, caller phone numbers or transcripts with personal data.
- `LATENCY_CASE_STUDY.md`, `DEV_JOURNEY.md`, `ELEVENLABS_INTEGRATION.md` are gitignored (interview prep). Use them as input if useful, but anything the article cites must live in tracked files under `docs/latency-post/`.

## Facts already in the repo (cite these, don't re-derive)

| Commit | Date | What it shows |
|---|---|---|
| `b5230f9` | 2026-05-20 | Switched to Claude Haiku for speed; ms timing in logs |
| `164ecce`, `71445e9`, `822bc76`, `0666aec` | May–Jun | speech_timeout tuned 1 s → 0.5 s → 1 s → 2 s (Hungarian sentences got cut off) — good "trade-off" story |
| `8f63642`, `fe4a10e`, `e01af9b` | 2026-05-20 | TTS speed vs quality: default Twilio voice was fastest but read Hungarian with an English accent → reverted |
| `9f5fdfd` | 2026-06-10 | Streaming Claude + concurrent TTS (start TTS at the first sentence boundary) |
| `221d1d7` | 2026-06-19 | Telnyx Call Control + Deepgram WebSocket STT pipeline |
| `caf7544` | 2026-06-20 | Deepgram nova-3 |
| `eb24776` | 2026-10-05 | TTS → ElevenLabs streaming (`eleven_turbo_v2_5`), shared httpx client in `tts_service.py` |
| `95f6a5f` | 2026-10-05 | Opt-in per-turn instrumentation (`LATENCY_DEBUG=1`, `api/services/latency_debug.py`) |
| `a89f78a` | 2026-10-05 | `LATENCY_REPORT.md` — stage map + ranked fixes |

⚠️ `LATENCY_REPORT.md` §2 measured TTS numbers (376–383 ms) are **Google TTS**, but the code now uses ElevenLabs. Re-measure the baseline before using any TTS number.

## Measurement protocol

- **Emulator (middle of pipeline):** on the droplet, `LATENCY_DEBUG=1 python3 call_emulator.py --no-audio` with a fixed set of ≥10 prompts (store them in `docs/latency-post/prompts.txt`), 2 rounds. Report median and p90.
- **Real calls (full turn):** ≥5 calls × 3 turns, same scripted questions. Collect with
  `docker compose -f docker-compose.prod.yml logs --since 15m api | grep LATENCY`.
- Add a parser script `docs/latency-post/parse_latency.py`: LATENCY log lines → `results.csv`.
- `results.csv` columns: `run_id, commit, date, source(emulator|call), turn, stage, delta_ms, total_ms`.
- Stages (already emitted): `speech_end_detected, stt_done, db_ready, llm_request_sent, llm_first_token, llm_done, tts_first_audio, audio_sent`.
- **Perceived end-to-end (what the caller actually hears):** István records the calls (speaker + second device, or call recording). Measure in the waveform (e.g. Audacity) from end of his speech to first audio of the reply, per turn. Store as `source=recording` rows in `results.csv` with stage `perceived_total`. This is the only way to see Telnyx's playback buffer, and it is the headline number for the post. The server-side `total_ms` explains *where* the time goes; the recording proves *how much* the caller waits.

## Work plan (in order; from LATENCY_REPORT.md §3, updated)

0. **Baseline** with current `main` (ElevenLabs). Commit `results.csv` + `docs: latency baseline`.
1. Reuse one `httpx.AsyncClient` in `callcontrol_service.py` (TTS already does). Init/close in FastAPI lifespan.
2. Remove redundant `SELECT call` in `routers/callcontrol.py`; move `_save_turn_to_db` off the hot path (background task with error logging).
3. Endpointing 500 → 300 ms (or Deepgram `utterance_end_ms`). Validate with Hungarian speech; revert if it cuts people off. Record false-endpoint count.
4. TTS model: try `eleven_flash_v2_5` vs `eleven_turbo_v2_5` (verify Hungarian support + quality by ear). Request mulaw/8 kHz output if Telnyx streaming allows, to skip MP3 decode.
5. Avoid the Telnyx → droplet audio GET: stream TTS frames back on the open Media Stream WS (bidirectional). Biggest refactor — only if 1–4 aren't enough.
6. Prompt: measure input tokens per tenant; trim base prompt; keep the cache warm.
7. Region experiment (optional): droplet is NYC1, callers are Hungarian/NZ. Measure before moving; don't migrate the DB just for the post.

Stop when the full turn median is under ~1.5 s or after step 5, whichever comes first.

## Deliverables (all under `docs/latency-post/`)

- `results.csv`, `prompts.txt`, `parse_latency.py`
- `waterfall.svg` + `waterfall.png` (1200×627, LinkedIn link-preview size): stacked horizontal bar per stage, **Before (baseline) vs After (final)**, total in big type ("5.x s → 1.x s"), commit short-hash under each improvement. Generate from `results.csv` with a script (`make_chart.py`), not by hand.
- `ARTICLE.md` (~800–1200 words, English): problem → how a voice turn breaks down → measurement → each fix with before/after and commit link → what didn't work (speech_timeout, default TTS voice) → final numbers → what's next.
- Web page for the link: `infoline.dev/blog/voice-latency` (or GitHub Pages) with
  `og:title`, `og:description`, `og:image` = `waterfall.png`. On LinkedIn the **link-preview card** is what's clickable — a plain image post would only open the image.
- Update `README.md` with a short "Latency" section linking the article.

## LinkedIn post draft (fill placeholders only from results.csv)

> My AI phone assistant made callers wait {BASELINE} s for every answer. On a phone line, that's an eternity.
>
> A voice turn is a relay race: end-of-speech detection → speech-to-text → LLM first token → tools → text-to-speech → network. I instrumented every leg on real calls instead of guessing.
>
> What moved the needle:
> • {FIX_1}: −{X} ms
> • {FIX_2}: −{Y} ms
> • {FIX_3}: −{Z} ms
>
> What didn't: shorter silence detection cut off Hungarian sentences, and the fastest TTS voice had an English accent. Speed you can't hear correctly isn't speed.
>
> Result: {BASELINE} s → {FINAL} s median. Every number links to a commit 👇
>
> {LINK — preview card shows waterfall.png}

## When done

Commit, push, and leave a 5-line summary at the top of `docs/latency-post/STATUS.md` (baseline, final, best fix, what failed, open issues). The chat will read it from there.
