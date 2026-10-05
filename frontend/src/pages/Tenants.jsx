import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl border border-gray-200 p-6 w-full max-w-md shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">{title}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-lg leading-none">&times;</button>
        </div>
        {children}
      </div>
    </div>
  )
}

function TenantForm({ initial = {}, onSubmit, loading, error }) {
  const [name, setName] = useState(initial.name ?? '')
  const [slug, setSlug] = useState(initial.slug ?? '')
  const [greeting, setGreeting] = useState(initial.greeting ?? '')
  const [prompt, setPrompt] = useState(initial.system_prompt ?? '')
  const [knowledgeBase, setKnowledgeBase] = useState(initial.knowledge_base ?? '')

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit({ name, slug, greeting: greeting || null, system_prompt: prompt || null, knowledge_base: knowledgeBase || null })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Slug</label>
        <input
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          required
          pattern="[a-z0-9-]+"
          title="Lowercase letters, digits, and hyphens only"
          disabled={!!initial.slug}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 disabled:bg-gray-50 disabled:text-gray-400"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Greeting</label>
        <textarea
          value={greeting}
          onChange={(e) => setGreeting(e.target.value)}
          rows={2}
          placeholder="e.g. Hello! I'm István Jancsó's AI agent."
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 resize-none"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">System prompt</label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={4}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 resize-none"
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Knowledge base</label>
        <textarea
          value={knowledgeBase}
          onChange={(e) => setKnowledgeBase(e.target.value)}
          rows={5}
          placeholder="Documents and information available to the AI…"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 resize-y"
        />
      </div>
      {error && <p className="text-red-500 text-xs">{error}</p>}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gray-900 text-white rounded-lg py-2 text-sm font-medium hover:bg-gray-700 disabled:opacity-40 transition-colors"
      >
        {loading ? 'Saving…' : 'Save'}
      </button>
    </form>
  )
}

export default function Tenants() {
  const [tenants, setTenants] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editTenant, setEditTenant] = useState(null)
  const [formLoading, setFormLoading] = useState(false)
  const [formError, setFormError] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await api.listTenants()
      setTenants(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleCreate(body) {
    setFormLoading(true)
    setFormError('')
    try {
      await api.createTenant(body)
      setShowCreate(false)
      load()
    } catch (e) {
      setFormError(e.message)
    } finally {
      setFormLoading(false)
    }
  }

  async function handleUpdate(body) {
    setFormLoading(true)
    setFormError('')
    try {
      await api.updateTenant(editTenant.id, body)
      setEditTenant(null)
      load()
    } catch (e) {
      setFormError(e.message)
    } finally {
      setFormLoading(false)
    }
  }

  async function handleDelete(tenant) {
    if (!confirm(`Delete tenant "${tenant.name}"? This cannot be undone.`)) return
    try {
      await api.deleteTenant(tenant.id)
      load()
    } catch (e) {
      alert(e.message)
    }
  }

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>
  if (error) return <p className="text-sm text-red-500">{error}</p>

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Tenants</h1>
        <button
          onClick={() => { setFormError(''); setShowCreate(true) }}
          className="bg-gray-900 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors"
        >
          + New tenant
        </button>
      </div>

      {tenants.length === 0 ? (
        <p className="text-sm text-gray-400">No tenants yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">Name</th>
                <th className="text-left px-4 py-3 font-medium">Slug</th>
                <th className="text-left px-4 py-3 font-medium">Created</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">
                    <Link to={`/tenants/${t.id}`} className="hover:underline">{t.name}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono">{t.slug}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(t.created_at).toLocaleDateString('en-US')}
                  </td>
                  <td className="px-4 py-3 text-right space-x-3">
                    <button
                      onClick={() => { setFormError(''); setEditTenant(t) }}
                      className="text-gray-400 hover:text-gray-700 text-xs"
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(t)}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <Modal title="New tenant" onClose={() => setShowCreate(false)}>
          <TenantForm onSubmit={handleCreate} loading={formLoading} error={formError} />
        </Modal>
      )}

      {editTenant && (
        <Modal title="Edit tenant" onClose={() => setEditTenant(null)}>
          <TenantForm
            initial={editTenant}
            onSubmit={handleUpdate}
            loading={formLoading}
            error={formError}
          />
        </Modal>
      )}
    </div>
  )
}
