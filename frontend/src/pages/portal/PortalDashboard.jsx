import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { tenantApi } from '../../lib/tenant-api'

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

function formatDuration(seconds) {
  if (seconds == null) return '—'
  if (seconds < 60) return `${seconds}s`
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
}

export default function PortalDashboard({ tenant }) {
  const [calls, setCalls] = useState([])
  const [phones, setPhones] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      tenantApi.listCalls(),
      tenantApi.listPhoneNumbers(),
    ]).then(([c, p]) => {
      setCalls(c)
      setPhones(p)
    }).finally(() => setLoading(false))
  }, [])

  const totalMinutes = calls.reduce((sum, c) => sum + (c.duration_seconds ?? 0), 0)
  const completedCalls = calls.filter((c) => c.status === 'completed').length

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">{tenant.name}</h1>
        <p className="text-sm text-gray-400 font-mono">{tenant.slug}</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard label="Total calls" value={calls.length} />
        <StatCard label="Successful calls" value={completedCalls} />
        <StatCard label="Total minutes" value={Math.ceil(totalMinutes / 60)} suffix="min" />
      </div>

      {phones.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-medium text-gray-700 mb-3">Phone numbers</h2>
          <div className="flex flex-wrap gap-2">
            {phones.map((p) => (
              <span key={p.id} className="bg-gray-100 text-gray-700 text-sm font-mono px-3 py-1.5 rounded-lg">
                {p.phone_number}{p.label ? ` · ${p.label}` : ''}
              </span>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="text-sm font-medium text-gray-700 mb-3">Recent calls</h2>
        {loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : calls.length === 0 ? (
          <p className="text-sm text-gray-400">No calls yet.</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                  <th className="text-left px-4 py-3 font-medium">Caller</th>
                  <th className="text-left px-4 py-3 font-medium">Status</th>
                  <th className="text-left px-4 py-3 font-medium">Duration</th>
                  <th className="text-left px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c) => (
                  <tr key={c.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-700">{c.from_number ?? '—'}</td>
                    <td className="px-4 py-3">
                      <Badge color={callStatusColor(c.status)}>{c.status ?? 'unknown'}</Badge>
                    </td>
                    <td className="px-4 py-3 text-gray-500">{formatDuration(c.duration_seconds)}</td>
                    <td className="px-4 py-3 text-gray-400">
                      {new Date(c.created_at).toLocaleString('en-US')}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/portal/calls/${c.id}`}
                        className="text-xs text-gray-400 hover:text-gray-700"
                      >
                        Transcript
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, suffix }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 px-5 py-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">
        {value}
        {suffix && <span className="text-sm font-normal text-gray-500 ml-1">{suffix}</span>}
      </p>
    </div>
  )
}
