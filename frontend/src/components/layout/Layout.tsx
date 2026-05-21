import { useState, useCallback, useMemo, type ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((v) => !v)
  }, [])

  const openMobile = useCallback(() => {
    setMobileOpen(true)
  }, [])

  const closeMobile = useCallback(() => {
    setMobileOpen(false)
  }, [])

  const sidebarWidth = sidebarCollapsed ? 64 : 240

  const mainStyle = useMemo(
    () => ({ '--sidebar-w': `${sidebarWidth}px` } as React.CSSProperties),
    [sidebarWidth],
  )

  return (
    <div className="flex h-screen overflow-hidden bg-surface-dark text-white">
      {/* 侧边栏 */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        mobileOpen={mobileOpen}
        onMobileClose={closeMobile}
      />

      {/* 右侧主体区域 - 桌面端跟随侧边栏宽度，移动端 ml-0 */}
      <div
        className="flex flex-1 flex-col overflow-hidden
                   transition-[margin-left] duration-300 ease-in-out
                   ml-0 lg:ml-[--sidebar-w]"
        style={mainStyle}
      >
        {/* 顶部栏 */}
        <Header onMenuClick={openMobile} sidebarCollapsed={sidebarCollapsed} />

        {/* 内容区域 */}
        <main
          className="flex-1 overflow-y-auto p-4 lg:p-6"
          style={{ scrollBehavior: 'smooth' }}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
