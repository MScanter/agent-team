import { Outlet, Link, useLocation } from 'react-router-dom'
import { Users, Bot, Play, Home, Settings } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { path: '/', label: '首页', icon: Home },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/teams', label: '团队', icon: Users },
  { path: '/models', label: 'API配置', icon: Settings },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-gray-800 border-r border-gray-700">
        <div className="flex items-center h-16 px-6 border-b border-gray-700">
          <Play className="w-8 h-8 text-primary-500" />
          <span className="ml-3 text-xl font-bold text-white">Agent Team</span>
        </div>

        <nav className="mt-6 px-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path

            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center px-4 py-3 mb-2 rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="ml-3">{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        <Outlet />
      </main>
    </div>
  )
}
