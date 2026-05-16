const getKey = () => localStorage.getItem('tenant_key') ?? ''

async function request(path, options = {}) {
  const res = await fetch(`/api/portal${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Key': getKey(),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('tenant_key')
    window.location.reload()
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Hiba történt')
  }
  if (res.status === 204) return null
  return res.json()
}

export const tenantApi = {
  getMe: () => request('/me'),
  updateMe: (body) => request('/me', { method: 'PATCH', body: JSON.stringify(body) }),
  listPhoneNumbers: () => request('/phone-numbers'),
  listCalls: (offset = 0, limit = 50) => request(`/calls?offset=${offset}&limit=${limit}`),
  getCall: (callId) => request(`/calls/${callId}`),
}
