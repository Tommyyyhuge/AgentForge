import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import Loading from '../ui/Loading'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * 路由守卫组件
 *
 * 检查用户是否已认证：
 * - 已认证：渲染子组件
 * - 未认证：重定向到登录页，保留原路径
 * - 加载中：显示 Loading
 */
export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuthStore()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-surface-bg">
        <Loading variant="spinner" text="加载中..." />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  return children
}
