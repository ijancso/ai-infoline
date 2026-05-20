const getKey = () => localStorage.getItem('admin_key') ?? ''

async function request(path, options = {}) {
  const res = await fetch(`/admin${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Admin-Key': getKey(),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('admin_key')
    window.location.reload()
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Hiba történt')
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Tenants
  listTenants: () => request('/tenants'),
  getTenant: (id) => request(`/tenants/${id}`),
  createTenant: (body) => request('/tenants', { method: 'POST', body: JSON.stringify(body) }),
  updateTenant: (id, body) => request(`/tenants/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteTenant: (id) => request(`/tenants/${id}`, { method: 'DELETE' }),

  // Phone numbers
  listPhoneNumbers: (tenantId) => request(`/tenants/${tenantId}/phone-numbers`),
  addPhoneNumber: (tenantId, body) =>
    request(`/tenants/${tenantId}/phone-numbers`, { method: 'POST', body: JSON.stringify(body) }),
  deletePhoneNumber: (tenantId, phoneId) =>
    request(`/tenants/${tenantId}/phone-numbers/${phoneId}`, { method: 'DELETE' }),

  // Calls
  listCalls: (tenantId) => request(`/tenants/${tenantId}/calls`),
  getCall: (tenantId, callId) => request(`/tenants/${tenantId}/calls/${callId}`),

  // Recordings
  listRecordings: (tenantId, callId) =>
    request(`/tenants/${tenantId}/calls/${callId}/recordings`),
}
