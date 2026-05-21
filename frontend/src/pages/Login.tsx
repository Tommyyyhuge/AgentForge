import { useState, useCallback, type FormEvent } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { LogIn, Eye, EyeOff, Bot, ArrowRight } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import Button from '../components/ui/Button'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string })?.from || '/'

  const { login, isLoading, error, clearError } = useAuthStore()

  const [form, setForm] = useState({
    username: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})

  const updateField = useCallback(
    (key: keyof typeof form, value: string) => {
      setForm((prev) => ({ ...prev, [key]: value }))
      if (formErrors[key]) {
        setFormErrors((prev) => {
          const next = { ...prev }
          delete next[key]
          return next
        })
      }
      if (error) clearError()
    },
    [formErrors, error, clearError]
  )

  const validate = useCallback(() => {
    const errors: Record<string, string> = {}
    if (!form.username.trim()) {
      errors.username = '请输入用户名'
    } else if (form.username.length < 3) {
      errors.username = '用户名至少 3 个字符'
    }
    if (!form.password) {
      errors.password = '请输入密码'
    } else if (form.password.length < 6) {
      errors.password = '密码至少 6 个字符'
    }
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }, [form])

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      if (!validate()) return

      try {
        await login(form.username, form.password)
        navigate(from, { replace: true })
      } catch {
        // 错误已在 authStore 中处理
      }
    },
    [form, validate, login, navigate, from]
  )

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-bg px-4">
      <motion.div
        className="w-full max-w-md"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-forge-500/10">
            <Bot className="h-6 w-6 text-forge-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">欢迎回来</h1>
          <p className="mt-2 text-sm text-neutral-400">
            登录 AgentForge 继续管理您的 AI 智能体
          </p>
        </div>

        {/* 表单 */}
        <form
          onSubmit={handleSubmit}
          className="space-y-4 rounded-forge border border-surface-border bg-surface-light p-6"
        >
          {/* 用户名 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">
              用户名
            </label>
            <input
              type="text"
              value={form.username}
              onChange={(e) => updateField('username', e.target.value)}
              placeholder="请输入用户名"
              className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                formErrors.username
                  ? 'border-red-500/50 focus:border-red-500'
                  : 'border-surface-border'
              }`}
              disabled={isLoading}
            />
            {formErrors.username && (
              <p className="mt-1 text-xs text-red-400">{formErrors.username}</p>
            )}
          </div>

          {/* 密码 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">
              密码
            </label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={form.password}
                onChange={(e) => updateField('password', e.target.value)}
                placeholder="请输入密码"
                className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 pr-10 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                  formErrors.password
                    ? 'border-red-500/50 focus:border-red-500'
                    : 'border-surface-border'
                }`}
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-white"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {formErrors.password && (
              <p className="mt-1 text-xs text-red-400">{formErrors.password}</p>
            )}
          </div>

          {/* 错误提示 */}
          {error && (
            <motion.div
              className="rounded-forge border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              {error}
            </motion.div>
          )}

          {/* 提交按钮 */}
          <Button
            type="submit"
            variant="primary"
            className="w-full"
            isLoading={isLoading}
            leftIcon={<LogIn className="h-4 w-4" />}
          >
            登录
          </Button>
        </form>

        {/* 注册链接 */}
        <p className="mt-6 text-center text-sm text-neutral-400">
          还没有账号？{' '}
          <Link
            to="/register"
            className="inline-flex items-center gap-1 font-medium text-forge-400 transition-colors hover:text-forge-300"
          >
            立即注册
            <ArrowRight className="h-3 w-3" />
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
