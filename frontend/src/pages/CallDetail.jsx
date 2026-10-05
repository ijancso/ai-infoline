import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'

function Badge({ children, color = 'gray' }) {
  const colors = {
    gray: 'bg-gray-100 text-gray-600',
    green: 'bg-green-100 text-green-700',
    red: 'bg-red-100 text-red-600',
    yellow: 'bg-yellow-100 text-yellow-700',
  }
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${colors[color]}`}>
      {children}
    </span>
  )
}

function callStatusColor(status) {
  if (!status) return 'gray'
  if (status === 'completed') return 'green'
  if (['failed', 'busy', 'no-answer'].includes(status)) return 'red'
  if (status === 'in-progress') return 'yellow'
  return 'gray'
}

function CallMeta({ call }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4 mb-6 grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Caller</p>
        <p className="font-mono text-gray-800">{call.from_number ?? '—'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Called</p>
        <p className="font-mono text-gray-800">{call.to_number ?? '—'}</p>
      </div>
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Status</p>
        <Badge color={callStatusColor(call.status)}>{call.status ?? 'unknown'}</Badge>
      </div>
      <div>
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Duration</p>
        <p className="text-gray-800">{call.duration_seconds != null ? `${call.duration_seconds} s` : '—'}</p>
      </div>
      <div className="col-span-2">
        <p className="text-xs text-gray-400 uppercase tracking-wide mb-0.5">Timestamp</p>
        <p className="text-gray-800">{new Date(call.created_at).toLocaleString('en-US')}</p>
      </div>
    </div>
  )
}

function Transcript({ messages }) {
  if (messages.length === 0) {
    return <p className="text-sm text-gray-400">No messages recorded for this call.</p>
  }

  return (
    <div className="space-y-2">
      {messages.map((m) => (
        <div
          key={m.id}
          className={`flex ${m.role === 'user' ? 'justify-start' : 'justify-end'}`}
        >
          <div
            className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === 'user'
                ? 'bg-gray-100 text-gray-800 rounded-tl-sm'
                : 'bg-gray-900 text-white rounded-tr-sm'
            }`}
          >
            <p className="text-[10px] font-medium mb-1 opacity-50 uppercase tracking-wide">
              {m.role === 'user' ? 'Caller' : 'AI'}
            </p>
            {m.content}
          </div>
        </div>
      ))}
    </div>
  )
}

function Recordings({ tenantId, callId }) {
  const [recordings, setRecordings] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listRecordings(tenantId, callId)
      .then(setRecordings)
      .finally(() => setLoading(false))
  }, [tenantId, callId])

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>
  if (recordings.length === 0) return <p className="text-sm text-gray-400">No recordings.</p>

  return (
    <div className="space-y-3">
      {recordings.map((r) => (
        <div key={r.id} className="bg-white rounded-xl border border-gray-200 px-4 py-3">
          <p className="text-sm font-mono text-gray-700">{r.recording_sid}</p>
          <p className="text-xs text-gray-400 mt-0.5">
            {r.duration_seconds != null ? `${r.duration_seconds} s` : 'unknown length'} ·{' '}
            {new Date(r.created_at).toLocaleString('en-US')}
          </p>
          <p className="text-xs text-gray-400 font-mono mt-1 truncate">{r.spaces_key}</p>
        </div>
      ))}
    </div>
  )
}

export default function CallDetail() {
  const { tenantId, callId } = useParams()
  const [call, setCall] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('transcript')

  useEffect(() => {
    api.getCall(tenantId, callId)
      .then(setCall)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [tenantId, callId])

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>
  if (error) return <p className="text-sm text-red-500">{error}</p>

  return (
    <div>
      <div className="mb-6">
        <Link to={`/tenants/${tenantId}`} className="text-xs text-gray-400 hover:text-gray-700">
          ← Back to tenant
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-1">Call details</h1>
        <p className="text-xs text-gray-400 font-mono mt-0.5">{call.call_sid}</p>
      </div>

      <CallMeta call={call} />

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {['transcript', 'recordings'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-400 hover:text-gray-700'
            }`}
          >
            {t === 'transcript' ? 'Transcript' : 'Recordings'}
          </button>
        ))}
      </div>

      {tab === 'transcript' && <Transcript messages={call.messages} />}
      {tab === 'recordings' && <Recordings tenantId={tenantId} callId={callId} />}
    </div>
  )
}
