import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { tenantApi } from '../../lib/tenant-api'

export default function PortalCallDetail() {
  const { callId } = useParams()
  const [call, setCall] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    tenantApi.getCall(callId).then(setCall).finally(() => setLoading(false))
  }, [callId])

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>
  if (!call) return <p className="text-sm text-red-500">Call not found.</p>

  return (
    <div>
      <div className="mb-6">
        <Link to="/portal" className="text-xs text-gray-400 hover:text-gray-700">← Calls</Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-1">Call details</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          {new Date(call.created_at).toLocaleString('en-US')}
          {call.duration_seconds != null && ` · ${call.duration_seconds}s`}
          {call.from_number && ` · ${call.from_number}`}
        </p>
      </div>

      {call.messages.length === 0 ? (
        <p className="text-sm text-gray-400">No messages recorded for this call.</p>
      ) : (
        <div className="space-y-3">
          {call.messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xl px-4 py-2.5 rounded-2xl text-sm ${
                  msg.role === 'user'
                    ? 'bg-gray-900 text-white rounded-br-sm'
                    : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>
                <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-gray-400' : 'text-gray-400'}`}>
                  {msg.role === 'user' ? 'Caller' : 'AI'}
                  {' · '}
                  {new Date(msg.created_at).toLocaleTimeString('en-US')}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
