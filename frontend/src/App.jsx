import { useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Login from './pages/Login'
import Tenants from './pages/Tenants'
import TenantDetail from './pages/TenantDetail'
import CallDetail from './pages/CallDetail'
import Layout from './components/Layout'
import PortalLayout from './components/PortalLayout'
import PortalLogin from './pages/portal/PortalLogin'
import PortalDashboard from './pages/portal/PortalDashboard'
import PortalCallDetail from './pages/portal/PortalCallDetail'
import PortalSettings from './pages/portal/PortalSettings'

function AdminApp() {
  const [adminKey, setAdminKey] = useState(() => localStorage.getItem('admin_key') ?? '')

  function handleLogin(key) {
    localStorage.setItem('admin_key', key)
    setAdminKey(key)
  }

  function handleLogout() {
    localStorage.removeItem('admin_key')
    setAdminKey('')
  }

  if (!adminKey) return <Login onLogin={handleLogin} />

  return (
    <Layout onLogout={handleLogout}>
      <Routes>
        <Route path="/" element={<Tenants />} />
        <Route path="/tenants/:tenantId" element={<TenantDetail />} />
        <Route path="/tenants/:tenantId/calls/:callId" element={<CallDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

function PortalApp() {
  const [tenantKey, setTenantKey] = useState(() => localStorage.getItem('tenant_key') ?? '')
  const [tenant, setTenant] = useState(() => {
    try { return JSON.parse(localStorage.getItem('tenant_data') ?? 'null') } catch { return null }
  })

  function handleLogin(key, tenantData) {
    localStorage.setItem('tenant_key', key)
    localStorage.setItem('tenant_data', JSON.stringify(tenantData))
    setTenantKey(key)
    setTenant(tenantData)
  }

  function handleLogout() {
    localStorage.removeItem('tenant_key')
    localStorage.removeItem('tenant_data')
    setTenantKey('')
    setTenant(null)
  }

  function handleTenantUpdate(updated) {
    localStorage.setItem('tenant_data', JSON.stringify(updated))
    setTenant(updated)
  }

  if (!tenantKey || !tenant) return <PortalLogin onLogin={handleLogin} />

  return (
    <PortalLayout tenant={tenant} onLogout={handleLogout}>
      <Routes>
        <Route path="/portal" element={<PortalDashboard tenant={tenant} />} />
        <Route path="/portal/calls/:callId" element={<PortalCallDetail />} />
        <Route path="/portal/settings" element={<PortalSettings tenant={tenant} onUpdate={handleTenantUpdate} />} />
        <Route path="*" element={<Navigate to="/portal" replace />} />
      </Routes>
    </PortalLayout>
  )
}

export default function App() {
  const location = useLocation()
  const isPortal = location.pathname.startsWith('/portal')

  if (isPortal) return <PortalApp />
  return <AdminApp />
}
