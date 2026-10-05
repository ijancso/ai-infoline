import { Link, useLocation } from 'react-router-dom'

export default function Layout({ children, onLogout }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold text-gray-900 text-sm tracking-wide">
            AI Infoline <span className="text-gray-400 font-normal">admin</span>
          </Link>
          <button
            onClick={onLogout}
            className="text-xs text-gray-500 hover:text-gray-900 transition-colors"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}
