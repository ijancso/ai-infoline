import { useState } from 'react'

export default function Login({ onLogin }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch('/admin/tenants', {
        headers: { 'X-Admin-Key': key },
      })
      if (res.status === 401) {
        setError('Invalid admin key.')
      } else {
        onLogin(key)
      }
    } catch {
      setError('Could not connect to the API.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl border border-gray-200 p-8 w-full max-w-sm shadow-sm">
        <h1 className="text-lg font-semibold text-gray-900 mb-1">AI Infoline</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in with admin key</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="password"
            placeholder="Admin key"
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
            {loading ? 'Checking…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
