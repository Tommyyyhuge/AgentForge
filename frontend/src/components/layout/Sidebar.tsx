import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ListTodo,
  Bot,
  MessageSquare,
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  User,
  LogIn,
  LogOut,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  mobileOpen: boolean
  onMobileClose: () => void
}

const NAV_ITEMS = [
  { to: '/',         label: '仪表盘', icon: LayoutDashboard },
  { to: '/tasks',    label: '任务',   icon: ListTodo },
  { to: '/agents',   label: 'Agents', icon: Bot },
  { to: '/chat',     label: '对话',   icon: MessageSquare },
  { to: '/settings', label: '设置',   icon: SettingsIcon },
]

const linkBase =
  'group flex items-center gap-3 rounded-forge px-3 py-2.5 text-sm font-medium transition-all duration-200'

export default function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const location = useLocation()
  const navigate = useNavigate()

  const { user, isAuthenticated, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
  }

  const handleLoginClick = () => {
    navigate('/settings')
    if (mobileOpen) onMobileClose()
  }

  // 移动端遮罩点击关闭
  const handleOverlayClick = () => {
    if (mobileOpen) onMobileClose()
  }

  const sidebarContent = (
    <aside
      className={`
        fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-surface-border
        bg-surface-dark transition-all duration-300 ease-in-out
        ${collapsed ? 'w-16' : 'w-60'}
      `}
    >
      {/* Logo 区域 */}
      <div
        className={`
          flex h-16 items-center border-b border-surface-border px-3
          ${collapsed ? 'justify-center' : 'justify-between'}
        `}
      >
        {!collapsed && (
          <div className="flex items-center gap-2.5 animate-fade-in">
            <Sparkles className="h-5 w-5 text-accent" />
            <span className="text-base font-semibold text-white">
              AgentForge
            </span>
          </div>
        )}
        {collapsed && <Sparkles className="h-5 w-5 text-accent" />}

        {/* 折叠按钮 - 桌面端 */}
        <button
          onClick={onToggle}
          className="hidden lg:flex h-7 w-7 items-center justify-center rounded-md
                     text-neutral-500 transition-colors hover:bg-white/5 hover:text-neutral-300"
          aria-label={collapsed ? '展开侧边栏' : '折叠侧边栏'}
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>

      {/* 导航项 */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = item.to === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.to)

          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => { if (mobileOpen) onMobileClose() }}
              className={`
                ${linkBase}
                ${isActive
                  ? 'bg-forge-500/15 text-forge-300'
                  : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }
                ${collapsed ? 'justify-center' : ''}
              `}
            >
              <Icon className={`h-5 w-5 shrink-0 ${isActive ? 'text-forge-400' : ''}`} />
              {!collapsed && (
                <span className="text-truncate">
                  {item.label}
                </span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* 底部：用户区域 + 版本号 */}
      <div className="border-t border-surface-border">
        {!collapsed ? (
          <>
            {/* 用户信息 */}
            <div className="px-3 pt-3 pb-2">
              {isAuthenticated && user ? (
                <div className="flex items-center gap-2.5">
                  {/* 头像 */}
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                                  bg-forge-500/15 text-forge-400 ring-1 ring-forge-500/20">
                    <User className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-neutral-300 truncate">{user.username}</p>
                    <p className="text-[10px] text-neutral-500 truncate">{user.email}</p>
                  </div>
                  <button
                    onClick={handleLogout}
                    className="shrink-0 rounded-md p-1 text-neutral-600 hover:text-red-400
                               hover:bg-red-500/5 transition-colors"
                    title="退出登录"
                  >
                    <LogOut className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleLoginClick}
                  className="flex w-full items-center gap-2 rounded-forge border border-surface-border
                             bg-white/[0.02] px-3 py-2 text-xs text-neutral-400
                             hover:border-forge-500/20 hover:bg-forge-500/5 hover:text-forge-400
                             transition-all duration-200"
                >
                  <LogIn className="h-3.5 w-3.5" />
                  登录 / 注册
                </button>
              )}
            </div>

            {/* 版本号 */}
            <div className="px-4 py-2">
              <p className="text-xs text-neutral-600">AgentForge v0.1.0</p>
            </div>
          </>
        ) : (
          /* 折叠态：只显示用户图标 + 版本 */
          <div className="flex flex-col items-center gap-2 py-3">
            {isAuthenticated && user ? (
              <div className="flex h-7 w-7 items-center justify-center rounded-full
                              bg-forge-500/15 text-forge-400 ring-1 ring-forge-500/20">
                <User className="h-3.5 w-3.5" />
              </div>
            ) : (
              <button
                onClick={handleLoginClick}
                className="flex h-7 w-7 items-center justify-center rounded-md text-neutral-600
                           hover:text-forge-400 hover:bg-forge-500/5 transition-colors"
                title="登录"
              >
                <LogIn className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  )

  return (
    <>
      {/* 桌面端直接渲染 */}
      <div className="hidden lg:block">{sidebarContent}</div>

      {/* 移动端：抽屉式 + 遮罩 */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 lg:hidden" onClick={handleOverlayClick}>
          {/* 遮罩 */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" />
          {/* 侧边栏 */}
          {sidebarContent}
        </div>
      )}
    </>
  )
}
