import { useState } from 'react'

export default function PortalLogin({ onLogin }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/api/portal/me', {
        headers: { 'X-Tenant-Key': key },
      })
      if (res.status === 401) {
        setError('Érvénytelen API kulcs.')
      } else if (!res.ok) {
        setError('Nem sikerült csatlakozni.')
      } else {
        const tenant = await res.json()
        onLogin(key, tenant)
      }
    } catch {
      setError('Nem sikerült csatlakozni az API-hoz.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl border border-gray-200 p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">AI Infoline</h1>
        <p className="text-sm text-gray-500 mb-6">Bérlői portál — belépés API kulccsal</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            placeholder="API kulcs"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
            autoFocus
          />
          {error && <p className="text-red-500 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={!key || loading}
            className="w-full bg-gray-900 text-white rounded-lg py-2 text-sm font-medium hover:bg-gray-700 disabled:opacity-40 transition-colors"
          >
            {loading ? 'Ellenőrzés...' : 'Belépés'}
          </button>
        </form>
      </div>
    </div>
  )
}
