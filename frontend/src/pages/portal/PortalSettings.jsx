import { useState } from 'react'
import { tenantApi } from '../../lib/tenant-api'

export default function PortalSettings({ tenant, onUpdate }) {
  const [prompt, setPrompt] = useState(tenant.system_prompt ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const updated = await tenantApi.updateMe({ system_prompt: prompt })
      onUpdate(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Beállítások</h1>

      <form onSubmit={handleSubmit} className="space-y-4 max-w-2xl">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            System prompt
          </label>
          <p className="text-xs text-gray-400 mb-2">
            Ez az utasítás határozza meg az AI viselkedését hívás közben.
          </p>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={10}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gray-900 resize-y"
            placeholder="Pl.: Te egy ügyfélszolgálatos asszisztens vagy..."
          />
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={saving}
          className="bg-gray-900 text-white text-sm px-5 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-40 transition-colors"
        >
          {saving ? 'Mentés...' : saved ? 'Mentve!' : 'Mentés'}
        </button>
      </form>
    </div>
  )
}
