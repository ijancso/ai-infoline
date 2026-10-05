import { Link, useLocation } from 'react-router-dom'

export default function PortalLayout({ children, tenant, onLogout }) {
  const location = useLocation()

  const navLinks = [
    { to: '/portal', label: 'Calls' },
    { to: '/portal/settings', label: 'Settings' },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <span className="font-semibold text-gray-900 text-sm tracking-wide">
              AI Infoline
            </span>
            <div className="flex gap-1">
              {navLinks.map(({ to, label }) => {
                const active = location.pathname === to
                return (
                  <Link
                    key={to}
                    to={to}
                    className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                      active
                        ? 'bg-gray-100 text-gray-900 font-medium'
                        : 'text-gray-500 hover:text-gray-900'
                    }`}
                  >
                    {label}
                  </Link>
                )
              })}
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-400">{tenant.name}</span>
            <button
              onClick={onLogout}
              className="text-xs text-gray-500 hover:text-gray-900 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
