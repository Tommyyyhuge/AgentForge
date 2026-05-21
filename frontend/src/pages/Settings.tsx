import { useState, useCallback, type FormEvent } from 'react'
import {
  Key,
  Moon,
  Sun,
  Monitor,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Eye,
  EyeOff,
  Save,
  RotateCcw,
  LogIn,
  UserPlus,
  LogOut,
  User,
  Mail,
  Lock,
  Shield,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'

// ============================================================
// 本地类型
// ============================================================

type Theme = 'light' | 'dark' | 'system'
type LogLevel = 'debug' | 'info' | 'warn' | 'error'
type AuthMode = 'login' | 'register'

interface SettingsData {
  kimiApiKey: string
  deepseekApiKey: string
  theme: Theme
  logLevel: LogLevel
}

interface AuthFormData {
  username: string
  password: string
  email: string
}

// ============================================================
// 常量
// ============================================================

const STORAGE_KEY = 'agentforge-settings'

const THEME_OPTIONS: { value: Theme; label: string; icon: React.ReactNode }[] = [
  { value: 'dark',   label: '深色',   icon: <Moon className="h-4 w-4" /> },
  { value: 'light',  label: '浅色',   icon: <Sun className="h-4 w-4" /> },
  { value: 'system', label: '跟随系统', icon: <Monitor className="h-4 w-4" /> },
]

const LOG_LEVEL_OPTIONS: { value: LogLevel; label: string; description: string }[] = [
  { value: 'debug', label: 'Debug',   description: '输出所有日志，包含详细调试信息' },
  { value: 'info',  label: 'Info',    description: '输出常规信息和重要事件' },
  { value: 'warn',  label: 'Warn',    description: '仅输出警告和错误信息' },
  { value: 'error', label: 'Error',   description: '仅输出错误信息（生产环境推荐）' },
]

const DEFAULT_SETTINGS: SettingsData = {
  kimiApiKey: '',
  deepseekApiKey: '',
  theme: 'dark',
  logLevel: 'info',
}

// ============================================================
// 辅助函数
// ============================================================

function loadSettings(): SettingsData {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) }
  } catch { /* 忽略解析错误 */ }
  return DEFAULT_SETTINGS
}

function saveSettings(data: SettingsData): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
}

// ============================================================
// 页面组件
// ============================================================

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData>(loadSettings)
  const [showKimiKey, setShowKimiKey] = useState(false)
  const [showDeepseekKey, setShowDeepseekKey] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [statusMessage, setStatusMessage] = useState('')

  // ===== 认证状态 =====
  const {
    user,
    isAuthenticated,
    isLoading: authLoading,
    error: authError,
    login,
    register,
    logout,
    clearError: clearAuthError,
  } = useAuthStore()

  const [authMode, setAuthMode] = useState<AuthMode>('login')
  const [authForm, setAuthForm] = useState<AuthFormData>({
    username: '',
    password: '',
    email: '',
  })

  const updateAuthField = useCallback(<K extends keyof AuthFormData>(key: K, value: AuthFormData[K]) => {
    setAuthForm((prev) => ({ ...prev, [key]: value }))
    if (authError) clearAuthError()
  }, [authError, clearAuthError])

  const handleAuthSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    try {
      if (authMode === 'login') {
        await login(authForm.username, authForm.password)
      } else {
        await register(authForm.username, authForm.password, authForm.email || undefined)
      }
      setAuthForm({ username: '', password: '', email: '' })
    } catch {
      // 错误已在 store 中处理
    }
  }, [authMode, authForm, login, register])

  const switchAuthMode = useCallback(() => {
    setAuthMode((prev) => (prev === 'login' ? 'register' : 'login'))
    clearAuthError()
  }, [clearAuthError])

  const handleLogout = useCallback(() => {
    logout()
  }, [logout])

  // 更新单个设置字段
  const updateSetting = useCallback(<K extends keyof SettingsData>(key: K, value: SettingsData[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }, [])

  // 保存设置
  const handleSave = useCallback((e?: FormEvent) => {
    e?.preventDefault()
    try {
      saveSettings(settings)
      setSaveStatus('success')
      setStatusMessage('设置已保存')
    } catch {
      setSaveStatus('error')
      setStatusMessage('保存失败，请重试')
    }
    setTimeout(() => { setSaveStatus('idle'); setStatusMessage('') }, 2500)
  }, [settings])

  // 重置为默认
  const handleReset = useCallback(() => {
    setSettings(DEFAULT_SETTINGS)
    setSaveStatus('success')
    setStatusMessage('已恢复默认设置')
    setTimeout(() => { setSaveStatus('idle'); setStatusMessage('') }, 2500)
  }, [])

  // 遮罩 API Key（中间部分显示为 *）
  const maskKey = (key: string): string => {
    if (!key) return ''
    if (key.length <= 12) return key
    return key.slice(0, 6) + '•'.repeat(Math.min(key.length - 12, 20)) + key.slice(-6)
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-slide-up">
      {/* 标题 */}
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">系统设置</h2>
        <p className="mt-1 text-sm text-neutral-400">管理 API Key、主题和日志级别</p>
      </div>

      {/* ======== 认证模块 ======== */}
      <section className="forge-card !bg-surface-dark space-y-5">
        <div className="flex items-center gap-2.5">
          <Shield className="h-5 w-5 text-forge-400" />
          <h3 className="text-base font-semibold text-white">账户</h3>
        </div>

        {isAuthenticated && user ? (
          /* ---- 已登录：展示用户信息 ---- */
          <div className="space-y-4">
            <div className="flex items-center gap-4 rounded-forge border border-surface-border bg-white/[0.02] p-4">
              {/* 头像占位 */}
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full
                              bg-forge-500/15 text-forge-400 ring-2 ring-forge-500/20">
                <User className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white truncate">{user.username}</p>
                <p className="text-xs text-neutral-400 truncate">{user.email}</p>
                <p className="mt-0.5 text-xs text-neutral-600 font-mono">ID: {user.id}</p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleLogout}
              className="forge-btn-ghost inline-flex items-center gap-2 text-neutral-400 hover:text-red-400"
            >
              <LogOut className="h-4 w-4" />
              退出登录
            </button>
          </div>
        ) : (
          /* ---- 未登录：登录 / 注册表单 ---- */
          <form onSubmit={handleAuthSubmit} className="space-y-4">
            {/* 模式切换 */}
            <div className="flex rounded-forge border border-surface-border bg-white/[0.02] p-1">
              <button
                type="button"
                onClick={() => switchAuthMode()}
                className={`
                  flex-1 flex items-center justify-center gap-1.5 rounded-md py-1.5 text-sm font-medium
                  transition-all duration-200
                  ${authMode === 'login'
                    ? 'bg-forge-500/15 text-forge-400'
                    : 'text-neutral-500 hover:text-neutral-300'
                  }
                `}
              >
                <LogIn className="h-4 w-4" />
                登录
              </button>
              <button
                type="button"
                onClick={() => switchAuthMode()}
                className={`
                  flex-1 flex items-center justify-center gap-1.5 rounded-md py-1.5 text-sm font-medium
                  transition-all duration-200
                  ${authMode === 'register'
                    ? 'bg-forge-500/15 text-forge-400'
                    : 'text-neutral-500 hover:text-neutral-300'
                  }
                `}
              >
                <UserPlus className="h-4 w-4" />
                注册
              </button>
            </div>

            {/* 用户名 */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-neutral-300">用户名</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                <input
                  type="text"
                  value={authForm.username}
                  onChange={(e) => updateAuthField('username', e.target.value)}
                  placeholder="输入用户名"
                  required
                  className="w-full rounded-forge border border-surface-border
                             bg-white/[0.03] py-2 pl-9 pr-3 text-sm text-white
                             placeholder:text-neutral-600
                             outline-none transition-colors
                             focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
                />
              </div>
            </div>

            {/* 邮箱（仅注册模式） */}
            {authMode === 'register' && (
              <div className="space-y-1.5 animate-fade-in">
                <label className="text-sm font-medium text-neutral-300">
                  邮箱 <span className="text-neutral-600">（选填）</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                  <input
                    type="email"
                    value={authForm.email}
                    onChange={(e) => updateAuthField('email', e.target.value)}
                    placeholder="your@email.com"
                    className="w-full rounded-forge border border-surface-border
                               bg-white/[0.03] py-2 pl-9 pr-3 text-sm text-white
                               placeholder:text-neutral-600
                               outline-none transition-colors
                               focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
                  />
                </div>
              </div>
            )}

            {/* 密码 */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-neutral-300">密码</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
                <input
                  type="password"
                  value={authForm.password}
                  onChange={(e) => updateAuthField('password', e.target.value)}
                  placeholder="输入密码"
                  required
                  className="w-full rounded-forge border border-surface-border
                             bg-white/[0.03] py-2 pl-9 pr-3 text-sm text-white
                             placeholder:text-neutral-600
                             outline-none transition-colors
                             focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
                />
              </div>
            </div>

            {/* 错误提示 */}
            {authError && (
              <div className="flex items-center gap-2 rounded-forge border border-red-500/20
                              bg-red-500/5 px-3 py-2 text-sm text-red-400 animate-fade-in">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{authError}</span>
              </div>
            )}

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={authLoading || !authForm.username || !authForm.password}
              className="forge-btn-primary w-full inline-flex items-center justify-center gap-2
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {authLoading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  处理中...
                </>
              ) : authMode === 'login' ? (
                <>
                  <LogIn className="h-4 w-4" />
                  登录
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  注册
                </>
              )}
            </button>
          </form>
        )}
      </section>

      <form onSubmit={handleSave} className="space-y-6">
        {/* ======== API Key 配置 ======== */}
        <section className="forge-card !bg-surface-dark space-y-5">
          <div className="flex items-center gap-2.5">
            <Key className="h-5 w-5 text-forge-400" />
            <h3 className="text-base font-semibold text-white">API Key</h3>
          </div>

          {/* Kimi API Key */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-neutral-300">Kimi API Key</label>
            <div className="relative">
              <input
                type={showKimiKey ? 'text' : 'password'}
                value={settings.kimiApiKey}
                onChange={(e) => updateSetting('kimiApiKey', e.target.value)}
                placeholder="sk-..."
                className="w-full rounded-forge border border-surface-border
                           bg-white/[0.03] py-2 pl-3 pr-10 text-sm text-white
                           placeholder:text-neutral-600 font-mono
                           outline-none transition-colors
                           focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
              />
              <button
                type="button"
                onClick={() => setShowKimiKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-500
                           transition-colors hover:text-neutral-300"
              >
                {showKimiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {settings.kimiApiKey && !showKimiKey && (
              <p className="text-xs text-neutral-600 font-mono">{maskKey(settings.kimiApiKey)}</p>
            )}
          </div>

          {/* DeepSeek API Key */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-neutral-300">DeepSeek API Key</label>
            <div className="relative">
              <input
                type={showDeepseekKey ? 'text' : 'password'}
                value={settings.deepseekApiKey}
                onChange={(e) => updateSetting('deepseekApiKey', e.target.value)}
                placeholder="sk-..."
                className="w-full rounded-forge border border-surface-border
                           bg-white/[0.03] py-2 pl-3 pr-10 text-sm text-white
                           placeholder:text-neutral-600 font-mono
                           outline-none transition-colors
                           focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
              />
              <button
                type="button"
                onClick={() => setShowDeepseekKey((v) => !v)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-neutral-500
                           transition-colors hover:text-neutral-300"
              >
                {showDeepseekKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {settings.deepseekApiKey && !showDeepseekKey && (
              <p className="text-xs text-neutral-600 font-mono">{maskKey(settings.deepseekApiKey)}</p>
            )}
          </div>

          <p className="text-xs text-neutral-600">
            API Key 仅保存在浏览器本地存储中，不会上传到服务器。
          </p>
        </section>

        {/* ======== 主题设置 ======== */}
        <section className="forge-card !bg-surface-dark space-y-4">
          <div className="flex items-center gap-2.5">
            {settings.theme === 'dark' ? (
              <Moon className="h-5 w-5 text-forge-400" />
            ) : settings.theme === 'light' ? (
              <Sun className="h-5 w-5 text-forge-400" />
            ) : (
              <Monitor className="h-5 w-5 text-forge-400" />
            )}
            <h3 className="text-base font-semibold text-white">主题</h3>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {THEME_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => updateSetting('theme', opt.value)}
                className={`
                  flex flex-col items-center gap-2 rounded-forge border px-4 py-3 text-sm
                  transition-all duration-200
                  ${settings.theme === opt.value
                    ? 'border-forge-500/40 bg-forge-500/10 text-forge-400'
                    : 'border-surface-border bg-white/[0.02] text-neutral-400 hover:border-surface-border/60 hover:text-neutral-300'
                  }
                `}
              >
                {opt.icon}
                <span>{opt.label}</span>
              </button>
            ))}
          </div>
        </section>

        {/* ======== 日志级别 ======== */}
        <section className="forge-card !bg-surface-dark space-y-4">
          <div className="flex items-center gap-2.5">
            <Sliders className="h-5 w-5 text-forge-400" />
            <h3 className="text-base font-semibold text-white">日志级别</h3>
          </div>

          <div className="space-y-2">
            {LOG_LEVEL_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`
                  flex cursor-pointer items-start gap-3 rounded-forge border px-4 py-3
                  transition-all duration-200
                  ${settings.logLevel === opt.value
                    ? 'border-forge-500/30 bg-forge-500/5'
                    : 'border-surface-border bg-white/[0.02] hover:border-surface-border/60'
                  }
                `}
              >
                <input
                  type="radio"
                  name="logLevel"
                  value={opt.value}
                  checked={settings.logLevel === opt.value}
                  onChange={() => updateSetting('logLevel', opt.value)}
                  className="mt-0.5 h-4 w-4 accent-forge-500"
                />
                <div>
                  <p className={`text-sm font-medium ${settings.logLevel === opt.value ? 'text-forge-400' : 'text-neutral-300'}`}>
                    {opt.label}
                  </p>
                  <p className="text-xs text-neutral-500">{opt.description}</p>
                </div>
              </label>
            ))}
          </div>
        </section>

        {/* ======== 操作按钮 ======== */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* 保存状态提示 */}
          <div className="flex items-center gap-2">
            {saveStatus === 'success' && (
              <span className="inline-flex items-center gap-1.5 text-sm text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                {statusMessage}
              </span>
            )}
            {saveStatus === 'error' && (
              <span className="inline-flex items-center gap-1.5 text-sm text-red-400">
                <AlertCircle className="h-4 w-4" />
                {statusMessage}
              </span>
            )}
          </div>

          {/* 按钮组 */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleReset}
              className="forge-btn-ghost inline-flex items-center gap-2 text-neutral-500 hover:text-red-400"
            >
              <RotateCcw className="h-4 w-4" />
              恢复默认
            </button>
            <button
              type="submit"
              className="forge-btn-primary inline-flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              保存设置
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
