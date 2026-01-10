import { Outlet, Link, useLocation } from 'react-router-dom'
import { Users, Bot, Play, Home, Settings } from 'lucide-react'
import clsx from 'clsx'

const navItems = [
  { path: '/', label: '首页', icon: Home },
  { path: '/agents', label: 'Agents', icon: Bot },
  { path: '/teams', label: '团队', icon: Users },
  { path: '/execution', label: '讨论', icon: Play },
  { path: '/models', label: 'API配置', icon: Settings },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-[#1a1a1a]">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-[#2d2d2d] border-r-4 border-black">
        <div className="flex items-center h-16 px-6 border-b-4 border-black">
          <Play className="w-8 h-8 text-primary-500 fill-current" />
          <span className="ml-3 text-lg font-press text-white tracking-tighter">AGENT-TEAM</span>
        </div>

        <nav className="mt-6 px-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)

            return (
              <Link
                key={item.path}
                to={item.path}
                className={clsx(
                  'flex items-center px-4 py-3 mb-2 border-2 transition-all font-pixel uppercase tracking-wide',
                  isActive
                    ? 'bg-primary-500 text-white border-black shadow-pixel-sm translate-x-[2px] translate-y-[2px]'
                    : 'text-gray-400 border-transparent hover:border-black hover:text-white hover:bg-gray-700'
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
