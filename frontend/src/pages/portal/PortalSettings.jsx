import { useState } from 'react'
import { tenantApi } from '../../lib/tenant-api'

export default function PortalSettings({ tenant, onUpdate }) {
  const [greeting, setGreeting] = useState(tenant.greeting ?? '')
  const [prompt, setPrompt] = useState(tenant.system_prompt ?? '')
  const [knowledgeBase, setKnowledgeBase] = useState(tenant.knowledge_base ?? '')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setSaved(false)
    setError('')
    try {
      const updated = await tenantApi.updateMe({ greeting: greeting || null, system_prompt: prompt, knowledge_base: knowledgeBase || null })
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
      <h1 className="text-xl font-semibold text-gray-900 mb-6">Settings</h1>

      <form onSubmit={handleSubmit} className="space-y-4 max-w-2xl">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Greeting
          </label>
          <p className="text-xs text-gray-400 mb-2">
            This is what the caller hears when the call connects.
          </p>
          <textarea
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
            rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 resize-none"
            placeholder="e.g. Hello! How can I help you?"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            System prompt
          </label>
          <p className="text-xs text-gray-400 mb-2">
            This instruction defines how the AI behaves during a call.
          </p>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={10}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gray-900 resize-y"
            placeholder="e.g. You are a customer service assistant…"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1.5">
            Knowledge base
          </label>
          <p className="text-xs text-gray-400 mb-2">
            Documents, company, or product info available to the AI.
          </p>
          <textarea
            value={knowledgeBase}
            onChange={(e) => setKnowledgeBase(e.target.value)}
            rows={12}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gray-900 resize-y"
            placeholder="e.g. Hours: Mon-Fri 9am-5pm. Products: ..."
          />
        </div>

        {error && <p className="text-xs text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={saving}
          className="bg-gray-900 text-white text-sm px-5 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-40 transition-colors"
        >
          {saving ? 'Saving…' : saved ? 'Saved!' : 'Save'}
        </button>
      </form>
    </div>
  )
}
