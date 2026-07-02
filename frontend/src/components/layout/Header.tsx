import { Menu, User } from 'lucide-react'

interface HeaderProps {
  onMenuClick: () => void
  sidebarCollapsed: boolean
}

export default function Header({ onMenuClick, sidebarCollapsed: _sc }: HeaderProps) {
  void _sc
  return (
    <header
      className="sticky top-0 z-30 flex h-16 items-center justify-between
                 border-b border-surface-border bg-surface-dark/95 px-4
                 backdrop-blur-md lg:px-6"
      style={{ marginLeft: 0 }}
    >
      {/* 左侧：移动端菜单按钮 + 标题 */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-md
                     text-neutral-400 transition-colors hover:bg-white/5
                     hover:text-neutral-200 lg:hidden"
          aria-label="打开菜单"
        >
          <Menu className="h-5 w-5" />
        </button>

        <h1 className="text-lg font-semibold text-white">
          AgentForge
        </h1>
      </div>

      {/* 右侧：用户区域 */}
      <div className="flex items-center gap-3">
        {/* 用户信息占位 */}
        <div className="flex items-center gap-2 rounded-forge px-3 py-1.5
                        transition-colors hover:bg-white/5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full
                          bg-forge-500/10 ring-1 ring-forge-500/20">
            <User className="h-4 w-4 text-forge-400" />
          </div>
          <div className="hidden text-sm sm:block">
            <p className="font-medium leading-none text-neutral-200">用户</p>
            <p className="mt-0.5 text-xs text-neutral-500">admin</p>
          </div>
        </div>
      </div>
    </header>
  )
}
