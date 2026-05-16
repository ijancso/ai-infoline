import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../lib/api'

export default function CallDetail() {
  const { tenantId, callId } = useParams()
  const [recordings, setRecordings] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.listRecordings(tenantId, callId)
      .then(setRecordings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [tenantId, callId])

  return (
    <div>
      <div className="mb-6">
        <Link to={`/tenants/${tenantId}`} className="text-xs text-gray-400 hover:text-gray-700">
          ← Vissza a tenanthoz
        </Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-1">Hívás részletei</h1>
        <p className="text-xs text-gray-400 font-mono mt-0.5">{callId}</p>
      </div>

      <h2 className="text-sm font-medium text-gray-700 mb-3">Felvételek</h2>

      {loading && <p className="text-sm text-gray-400">Betöltés...</p>}
      {error && <p className="text-sm text-red-500">{error}</p>}

      {!loading && !error && recordings.length === 0 && (
        <p className="text-sm text-gray-400">Nincs felvétel ehhez a híváshoz.</p>
      )}

      {recordings.length > 0 && (
        <div className="space-y-3">
          {recordings.map((r) => (
            <div key={r.id} className="bg-white rounded-xl border border-gray-200 px-4 py-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-mono text-gray-700">{r.recording_sid}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {r.duration_seconds != null ? `${r.duration_seconds}s` : 'ismeretlen hossz'} ·{' '}
                    {new Date(r.created_at).toLocaleString('hu')}
                  </p>
                </div>
                <p className="text-xs text-gray-400 font-mono truncate max-w-xs text-right">
                  {r.spaces_key}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
