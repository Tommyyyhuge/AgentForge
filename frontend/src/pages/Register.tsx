import { useState, useCallback, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { UserPlus, Eye, EyeOff, Bot, ArrowLeft } from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import Button from '../components/ui/Button'

export default function Register() {
  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()

  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
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

    // 用户名
    if (!form.username.trim()) {
      errors.username = '请输入用户名'
    } else if (!/^[a-zA-Z0-9_]{3,20}$/.test(form.username)) {
      errors.username = '用户名 3-20 位，仅允许字母、数字、下划线'
    }

    // 邮箱
    if (!form.email.trim()) {
      errors.email = '请输入邮箱'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errors.email = '邮箱格式不正确'
    }

    // 密码
    if (!form.password) {
      errors.password = '请输入密码'
    } else if (form.password.length < 8) {
      errors.password = '密码至少 8 个字符'
    } else if (!/(?=.*[A-Za-z])(?=.*\d)/.test(form.password)) {
      errors.password = '密码需包含字母和数字'
    }

    // 确认密码
    if (form.password !== form.confirmPassword) {
      errors.confirmPassword = '两次输入的密码不一致'
    }

    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }, [form])

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault()
      if (!validate()) return

      try {
        await register(form.username, form.password, form.email)
        navigate('/', { replace: true })
      } catch {
        // 错误已在 authStore 中处理
      }
    },
    [form, validate, register, navigate]
  )

  // 密码强度
  const passwordStrength = useCallback(() => {
    if (!form.password) return 0
    let score = 0
    if (form.password.length >= 8) score++
    if (form.password.length >= 12) score++
    if (/[a-z]/.test(form.password) && /[A-Z]/.test(form.password)) score++
    if (/\d/.test(form.password)) score++
    if (/[^A-Za-z0-9]/.test(form.password)) score++
    return Math.min(score, 4)
  }, [form.password])

  const strength = passwordStrength()
  const strengthLabels = ['弱', '一般', '良好', '强']
  const strengthColors = ['bg-red-500', 'bg-amber-500', 'bg-forge-500', 'bg-emerald-500']

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
          <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-forge bg-brand-primary/10">
            <Bot className="h-6 w-6 text-forge-400" />
          </div>
          <h1 className="text-2xl font-bold text-white">创建账号</h1>
          <p className="mt-2 text-sm text-neutral-400">
            注册 AgentForge 开始构建您的 AI 智能体团队
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
              placeholder="3-20 位字母、数字、下划线"
              className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                formErrors.username ? 'border-red-500/50' : 'border-surface-border'
              }`}
              disabled={isLoading}
            />
            {formErrors.username && (
              <p className="mt-1 text-xs text-red-400">{formErrors.username}</p>
            )}
          </div>

          {/* 邮箱 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">
              邮箱
            </label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => updateField('email', e.target.value)}
              placeholder="your@email.com"
              className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                formErrors.email ? 'border-red-500/50' : 'border-surface-border'
              }`}
              disabled={isLoading}
            />
            {formErrors.email && (
              <p className="mt-1 text-xs text-red-400">{formErrors.email}</p>
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
                placeholder="至少 8 位，包含字母和数字"
                className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 pr-10 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                  formErrors.password ? 'border-red-500/50' : 'border-surface-border'
                }`}
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-white"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {/* 密码强度 */}
            {form.password && (
              <div className="mt-2">
                <div className="flex gap-1">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors ${
                        i <= strength ? strengthColors[strength - 1] : 'bg-neutral-700'
                      }`}
                    />
                  ))}
                </div>
                <p className="mt-1 text-xs text-neutral-400">
                  密码强度：{strengthLabels[strength - 1] || '弱'}
                </p>
              </div>
            )}
            {formErrors.password && (
              <p className="mt-1 text-xs text-red-400">{formErrors.password}</p>
            )}
          </div>

          {/* 确认密码 */}
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">
              确认密码
            </label>
            <input
              type="password"
              value={form.confirmPassword}
              onChange={(e) => updateField('confirmPassword', e.target.value)}
              placeholder="再次输入密码"
              className={`w-full rounded-forge border bg-surface-bg px-4 py-2.5 text-sm text-white placeholder-neutral-500 transition-colors focus:border-forge-500 focus:outline-none focus:ring-1 focus:ring-forge-500/30 ${
                formErrors.confirmPassword ? 'border-red-500/50' : 'border-surface-border'
              }`}
              disabled={isLoading}
            />
            {formErrors.confirmPassword && (
              <p className="mt-1 text-xs text-red-400">{formErrors.confirmPassword}</p>
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
            leftIcon={<UserPlus className="h-4 w-4" />}
          >
            注册
          </Button>
        </form>

        {/* 登录链接 */}
        <p className="mt-6 text-center text-sm text-neutral-400">
          已有账号？{' '}
          <Link
            to="/login"
            className="inline-flex items-center gap-1 font-medium text-forge-400 transition-colors hover:text-forge-300"
          >
            <ArrowLeft className="h-3 w-3" />
            去登录
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
