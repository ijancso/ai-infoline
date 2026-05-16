import { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Tenants from './pages/Tenants'
import TenantDetail from './pages/TenantDetail'
import CallDetail from './pages/CallDetail'
import Layout from './components/Layout'

export default function App() {
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
