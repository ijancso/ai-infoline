import { useState, useEffect, useCallback } from 'react'
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

function ApiKeyBox({ apiKey }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mb-6 flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="text-xs font-medium text-blue-600 mb-0.5 uppercase tracking-wide">Tenant API kulcs</p>
        <p className="text-sm font-mono text-blue-900 truncate">{apiKey}</p>
      </div>
      <button
        onClick={handleCopy}
        className="shrink-0 text-xs text-blue-600 hover:text-blue-800 border border-blue-300 rounded px-2 py-1 transition-colors"
      >
        {copied ? 'Másolva!' : 'Másolás'}
      </button>
    </div>
  )
}

function callStatusColor(status) {
  if (!status) return 'gray'
  if (status === 'completed') return 'green'
  if (['failed', 'busy', 'no-answer'].includes(status)) return 'red'
  if (status === 'in-progress') return 'yellow'
  return 'gray'
}

function PhoneNumbers({ tenantId }) {
  const [phones, setPhones] = useState([])
  const [loading, setLoading] = useState(true)
  const [number, setNumber] = useState('')
  const [label, setLabel] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const data = await api.listPhoneNumbers(tenantId)
      setPhones(data)
    } finally {
      setLoading(false)
    }
  }, [tenantId])

  useEffect(() => { load() }, [load])

  async function handleAdd(e) {
    e.preventDefault()
    setAdding(true)
    setError('')
    try {
      await api.addPhoneNumber(tenantId, { phone_number: number, label: label || null })
      setNumber('')
      setLabel('')
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setAdding(false)
    }
  }

  async function handleDelete(phone) {
    if (!confirm(`Törlöd a ${phone.phone_number} számot?`)) return
    try {
      await api.deletePhoneNumber(tenantId, phone.id)
      load()
    } catch (e) {
      alert(e.message)
    }
  }

  if (loading) return <p className="text-sm text-gray-400">Betöltés...</p>

  return (
    <div className="space-y-4">
      <form onSubmit={handleAdd} className="flex gap-2">
        <input
          value={number}
          onChange={(e) => setNumber(e.target.value)}
          placeholder="+36301234567"
          required
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 w-44"
        />
        <input
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="Címke (opcionális)"
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-900 flex-1"
        />
        <button
          type="submit"
          disabled={adding}
          className="bg-gray-900 text-white text-sm px-4 py-2 rounded-lg hover:bg-gray-700 disabled:opacity-40 transition-colors whitespace-nowrap"
        >
          + Hozzáadás
        </button>
      </form>
      {error && <p className="text-xs text-red-500">{error}</p>}

      {phones.length === 0 ? (
        <p className="text-sm text-gray-400">Még nincs telefonszám.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                <th className="text-left px-4 py-3 font-medium">Szám</th>
                <th className="text-left px-4 py-3 font-medium">Címke</th>
                <th className="text-left px-4 py-3 font-medium">Hozzáadva</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {phones.map((p) => (
                <tr key={p.id} className="border-b border-gray-50 last:border-0">
                  <td className="px-4 py-3 font-mono text-gray-900">{p.phone_number}</td>
                  <td className="px-4 py-3 text-gray-500">{p.label ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {new Date(p.created_at).toLocaleDateString('hu')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(p)}
                      className="text-red-400 hover:text-red-600 text-xs"
                    >
                      Törlés
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Calls({ tenantId }) {
  const [calls, setCalls] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.listCalls(tenantId).then(setCalls).finally(() => setLoading(false))
  }, [tenantId])

  if (loading) return <p className="text-sm text-gray-400">Betöltés...</p>

  if (calls.length === 0) return <p className="text-sm text-gray-400">Még nem volt hívás.</p>

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
            <th className="text-left px-4 py-3 font-medium">Hívó</th>
            <th className="text-left px-4 py-3 font-medium">Hívott</th>
            <th className="text-left px-4 py-3 font-medium">Státusz</th>
            <th className="text-left px-4 py-3 font-medium">Időtartam</th>
            <th className="text-left px-4 py-3 font-medium">Dátum</th>
            <th className="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c) => (
            <tr key={c.id} className="border-b border-gray-50 last:border-0 hover:bg-gray-50">
              <td className="px-4 py-3 font-mono text-gray-700">{c.from_number ?? '—'}</td>
              <td className="px-4 py-3 font-mono text-gray-700">{c.to_number ?? '—'}</td>
              <td className="px-4 py-3">
                <Badge color={callStatusColor(c.status)}>{c.status ?? 'ismeretlen'}</Badge>
              </td>
              <td className="px-4 py-3 text-gray-500">
                {c.duration_seconds != null ? `${c.duration_seconds}s` : '—'}
              </td>
              <td className="px-4 py-3 text-gray-400">
                {new Date(c.created_at).toLocaleString('hu')}
              </td>
              <td className="px-4 py-3 text-right">
                <Link
                  to={`/tenants/${tenantId}/calls/${c.id}`}
                  className="text-xs text-gray-400 hover:text-gray-700"
                >
                  Részletek
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function TenantDetail() {
  const { tenantId } = useParams()
  const [tenant, setTenant] = useState(null)
  const [tab, setTab] = useState('calls')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getTenant(tenantId).then(setTenant).finally(() => setLoading(false))
  }, [tenantId])

  if (loading) return <p className="text-sm text-gray-400">Betöltés...</p>
  if (!tenant) return <p className="text-sm text-red-500">Tenant nem található.</p>

  return (
    <div>
      <div className="mb-6">
        <Link to="/" className="text-xs text-gray-400 hover:text-gray-700">← Tenantok</Link>
        <h1 className="text-xl font-semibold text-gray-900 mt-1">{tenant.name}</h1>
        <p className="text-sm text-gray-400 font-mono">{tenant.slug}</p>
      </div>

      <ApiKeyBox apiKey={tenant.api_key} />

      {tenant.system_prompt && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 mb-6">
          <p className="text-xs font-medium text-gray-500 mb-1 uppercase tracking-wide">System prompt</p>
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{tenant.system_prompt}</p>
        </div>
      )}

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {['calls', 'phones'].map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-400 hover:text-gray-700'
            }`}
          >
            {t === 'calls' ? 'Hívások' : 'Telefonszámok'}
          </button>
        ))}
      </div>

      {tab === 'calls' && <Calls tenantId={tenantId} />}
      {tab === 'phones' && <PhoneNumbers tenantId={tenantId} />}
    </div>
  )
}
