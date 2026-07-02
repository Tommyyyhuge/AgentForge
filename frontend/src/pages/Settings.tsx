import { useState, useCallback, useEffect, useMemo, type FormEvent } from 'react'
import {
  Key,
  Moon,
  Sun,
  Monitor,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Save,
  RotateCcw,
  LogIn,
  UserPlus,
  LogOut,
  User,
  Mail,
  Lock,
  Shield,
  Plus,
  Trash2,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { useProviderStore } from '../stores/providerStore'
import { useTheme } from '../hooks/useTheme'
import { createApiKey, deleteApiKey, fetchApiKeys, getApiErrorMessage } from '../api/apiKeys'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import type {
  ApiKey,
  ApiKeyPermission,
  CreateProviderFromPresetInput,
  CreateRelayProviderInput,
  ProviderCapabilities,
  ProviderConfig,
  ProviderModelsResult,
  ProviderPreset,
  ProviderType,
} from '../types'

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
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [statusMessage, setStatusMessage] = useState('')

  // ===== 主题状态 =====
  const { theme: currentTheme, setTheme } = useTheme()

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
    // 同步更新主题
    if (key === 'theme') {
      setTheme(value as 'light' | 'dark' | 'system')
    }
  }, [setTheme])

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

  // 遮罩 API Key 已由服务端加密 API 替代，不再需要客户端处理

  return (
    <div className="mx-auto max-w-3xl space-y-6 animate-slide-up">
      {/* 标题 */}
      <div>
        <h2 className="text-2xl font-bold text-white">系统设置</h2>
        <p className="mt-1 text-sm text-neutral-400">管理 API Key、主题和日志级别</p>
      </div>
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

      <ProviderSettingsSection />

      <form onSubmit={handleSave} className="space-y-6">
        <APIKeySection />
        <section className="forge-card !bg-surface-dark space-y-4">
          <div className="flex items-center gap-2.5">
            {currentTheme === 'dark' ? (
              <Moon className="h-5 w-5 text-forge-400" />
            ) : currentTheme === 'light' ? (
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
                  ${currentTheme === opt.value
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

// ============================================================
// API Key 管理组件
// ============================================================

type ProviderFormState = CreateRelayProviderInput & {
  providerType: ProviderType
  capabilities: ProviderCapabilities
}

const RELAY_PROVIDER_CAPABILITIES: ProviderCapabilities = {
  chat: true,
  streaming: false,
  tool_calling: false,
  json_mode: false,
  vision: false,
  embeddings: false,
  model_listing: false,
  usage_reporting: false,
}

const FALLBACK_RELAY_PRESET: ProviderPreset = {
  providerType: 'openai_compatible',
  displayName: 'OpenAI-compatible relay',
  implementationStatus: 'implemented',
  authType: 'api_key_bearer',
  capabilities: RELAY_PROVIDER_CAPABILITIES,
  aliases: [],
  isRelay: true,
}

const CAPABILITY_LABELS: Array<[keyof ProviderCapabilities, string]> = [
  ['chat', 'Chat'],
  ['streaming', 'Streaming'],
  ['tool_calling', 'Tools'],
  ['json_mode', 'JSON'],
  ['vision', 'Vision'],
  ['embeddings', 'Embeddings'],
  ['model_listing', 'Models'],
  ['usage_reporting', 'Usage'],
]

const DEFAULT_PROVIDER_FORM: ProviderFormState = {
  providerType: 'openai_compatible',
  displayName: '',
  baseUrl: '',
  apiKey: '',
  defaultModel: '',
  capabilities: RELAY_PROVIDER_CAPABILITIES,
  streamingEnabled: false,
  toolCallingEnabled: false,
  timeoutSeconds: 60,
}

function ProviderSettingsSection() {
  const {
    presets,
    providers,
    modelsByProviderId,
    healthByProviderId,
    isLoading,
    isSaving,
    testingProviderId,
    error,
    validationError,
    fetchProviderSettings,
    createRelayProvider,
    createProviderFromPreset,
    testProviderConfig,
    loadProviderModels,
    deleteProviderConfig,
    clearError,
  } = useProviderStore()
  const [form, setForm] = useState<ProviderFormState>(DEFAULT_PROVIDER_FORM)

  useEffect(() => {
    void fetchProviderSettings()
  }, [fetchProviderSettings])

  const selectablePresets = useMemo(() => {
    const implementedPresets = presets.filter((preset) => preset.implementationStatus === 'implemented')
    return implementedPresets.length > 0 ? implementedPresets : [FALLBACK_RELAY_PRESET]
  }, [presets])

  const selectedPreset = selectablePresets.find((preset) => preset.providerType === form.providerType)

  const updateForm = useCallback(<K extends keyof ProviderFormState>(
    key: K,
    value: ProviderFormState[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (error || validationError) clearError()
  }, [clearError, error, validationError])

  const updateCapabilityToggle = useCallback((
    capability: 'streaming' | 'tool_calling',
    checked: boolean,
  ) => {
    const enabledKey = capability === 'streaming' ? 'streamingEnabled' : 'toolCallingEnabled'
    setForm((prev) => ({
      ...prev,
      [enabledKey]: checked,
      capabilities: {
        ...prev.capabilities,
        [capability]: checked,
      },
    }))
    if (error || validationError) clearError()
  }, [clearError, error, validationError])

  const handleProviderTypeChange = useCallback((providerType: ProviderType) => {
    const preset = selectablePresets.find((candidate) => candidate.providerType === providerType)
    if (!preset) return

    setForm((prev) => ({
      ...prev,
      providerType,
      displayName: preset.displayName,
      baseUrl: preset.baseUrl ?? '',
      defaultModel: preset.defaultModel ?? '',
      capabilities: { ...preset.capabilities },
      streamingEnabled: preset.capabilities.streaming,
      toolCallingEnabled: preset.capabilities.tool_calling,
    }))
    if (error || validationError) clearError()
  }, [clearError, error, selectablePresets, validationError])

  const handleSaveProvider = useCallback(async () => {
    if (form.providerType === 'openai_compatible') {
      await createRelayProvider({
        displayName: form.displayName,
        baseUrl: form.baseUrl,
        apiKey: form.apiKey,
        defaultModel: form.defaultModel,
        streamingEnabled: form.streamingEnabled,
        toolCallingEnabled: form.toolCallingEnabled,
        timeoutSeconds: form.timeoutSeconds,
      })
      return
    }

    const providerFromPreset: CreateProviderFromPresetInput = {
      providerType: form.providerType,
      displayName: form.displayName,
      baseUrl: form.baseUrl || undefined,
      apiKey: form.apiKey,
      defaultModel: form.defaultModel,
      capabilities: form.capabilities,
      streamingEnabled: form.streamingEnabled,
      toolCallingEnabled: form.toolCallingEnabled,
      timeoutSeconds: form.timeoutSeconds,
    }
    await createProviderFromPreset(providerFromPreset)
  }, [createProviderFromPreset, createRelayProvider, form])

  return (
    <section className="forge-card !bg-surface-dark space-y-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <Sliders className="h-5 w-5 text-forge-400" />
          <h3 className="text-base font-semibold text-white">Provider Configuration</h3>
        </div>
        {selectedPreset && (
          <span className="rounded-forge border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">
            {selectedPreset.displayName}
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="rounded-forge border border-surface-border bg-white/[0.02] px-4 py-3 text-sm text-neutral-400">
          Loading Provider settings...
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-forge border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : providers.length > 0 ? (
        <div className="space-y-2">
          {providers.map((provider) => (
            <ProviderConfigRow
              key={provider.id}
              provider={provider}
              health={healthByProviderId[provider.id]}
              models={modelsByProviderId[provider.id]}
              isTesting={testingProviderId === provider.id}
              onTest={(modelId) => testProviderConfig(provider.id, modelId || provider.defaultModel)}
              onLoadModels={() => loadProviderModels(provider.id)}
              onDelete={() => deleteProviderConfig(provider.id)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-forge border border-dashed border-surface-border bg-white/[0.02] px-4 py-3 text-sm text-neutral-400">
          No Provider configs yet.
        </div>
      )}

      <div className="grid gap-4 rounded-forge border border-surface-border bg-white/[0.02] p-4 md:grid-cols-2">
        <div className="space-y-1.5">
          <label htmlFor="provider-type" className="text-sm font-medium text-neutral-300">
            Provider type
          </label>
          <select
            id="provider-type"
            value={form.providerType}
            onChange={(event) => handleProviderTypeChange(event.target.value as ProviderType)}
            className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 text-sm text-white outline-none focus:border-forge-500"
          >
            {selectablePresets.map((preset) => (
              <option key={preset.providerType} value={preset.providerType}>
                {preset.displayName}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="provider-display-name" className="text-sm font-medium text-neutral-300">
            Display name
          </label>
          <input
            id="provider-display-name"
            type="text"
            value={form.displayName}
            onChange={(event) => updateForm('displayName', event.target.value)}
            className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 text-sm text-white outline-none focus:border-forge-500"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="provider-base-url" className="text-sm font-medium text-neutral-300">
            Base URL
          </label>
          <input
            id="provider-base-url"
            type="url"
            value={form.baseUrl}
            onChange={(event) => updateForm('baseUrl', event.target.value)}
            placeholder="https://relay.example/v1"
            className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 font-mono text-sm text-white outline-none placeholder:text-neutral-600 focus:border-forge-500"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="provider-api-key" className="text-sm font-medium text-neutral-300">
            API Key
          </label>
          <input
            id="provider-api-key"
            type="password"
            value={form.apiKey}
            onChange={(event) => updateForm('apiKey', event.target.value)}
            placeholder="sk-..."
            className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 font-mono text-sm text-white outline-none placeholder:text-neutral-600 focus:border-forge-500"
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="provider-default-model" className="text-sm font-medium text-neutral-300">
            Default model
          </label>
          <input
            id="provider-default-model"
            type="text"
            value={form.defaultModel}
            onChange={(event) => updateForm('defaultModel', event.target.value)}
            className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 font-mono text-sm text-white outline-none focus:border-forge-500"
          />
        </div>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input
            type="checkbox"
            checked={form.streamingEnabled}
            onChange={(event) => updateCapabilityToggle('streaming', event.target.checked)}
            className="h-4 w-4 accent-forge-500"
          />
          Streaming
        </label>
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          <input
            type="checkbox"
            checked={form.toolCallingEnabled}
            onChange={(event) => updateCapabilityToggle('tool_calling', event.target.checked)}
            className="h-4 w-4 accent-forge-500"
          />
          Tool calling
        </label>
        <div className="flex flex-wrap gap-1.5 md:col-span-2">
          {CAPABILITY_LABELS.map(([capability, label]) => (
            <span
              key={capability}
              className={`rounded border px-2 py-0.5 text-xs ${
                form.capabilities[capability]
                  ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                  : 'border-surface-border text-neutral-500'
              }`}
            >
              {label}
            </span>
          ))}
        </div>
      </div>

      {validationError && (
        <p className="text-sm text-red-400">{validationError}</p>
      )}

      <Button
        type="button"
        variant="primary"
        size="sm"
        isLoading={isSaving}
        onClick={handleSaveProvider}
        leftIcon={<Plus className="h-4 w-4" />}
      >
        Save Provider
      </Button>
    </section>
  )
}

function ProviderConfigRow({
  provider,
  health,
  models,
  isTesting,
  onTest,
  onLoadModels,
  onDelete,
}: {
  provider: ProviderConfig
  health?: { status: string; errorCode?: string; errorMessage?: string }
  models?: ProviderModelsResult
  isTesting: boolean
  onTest: (modelId?: string) => void
  onLoadModels: () => void
  onDelete: () => void
}) {
  const healthLabel = health?.status ?? 'unknown'
  const availableModels = models?.models ?? []
  const [selectedModel, setSelectedModel] = useState(provider.defaultModel || availableModels[0]?.id || '')
  const [manualModel, setManualModel] = useState(provider.defaultModel || '')
  const defaultListedModel = availableModels.find((model) => model.id === provider.defaultModel)?.id
  const selectedListedModel = availableModels.find((model) => model.id === selectedModel)?.id
  const selectedModelValue = selectedListedModel || defaultListedModel || availableModels[0]?.id || ''
  const modelForTest = availableModels.length > 0
    ? selectedModelValue
    : manualModel || provider.defaultModel

  return (
    <div className="rounded-forge border border-surface-border bg-white/[0.02] px-4 py-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{provider.displayName}</p>
          <p className="truncate font-mono text-xs text-neutral-500">{provider.baseUrl}</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className="rounded border border-surface-border px-2 py-0.5 text-xs text-neutral-400">
              {provider.providerType}
            </span>
            <span className="rounded border border-surface-border px-2 py-0.5 text-xs text-neutral-400">
              {provider.defaultModel || 'manual model'}
            </span>
            <span className="rounded border border-surface-border px-2 py-0.5 text-xs text-neutral-400">
              health: {healthLabel}
            </span>
          </div>
          {health?.errorMessage && (
            <p className="mt-2 text-xs text-red-400">{health.errorMessage}</p>
          )}
          {models?.status === 'degraded' && (
            <p className="mt-2 text-xs text-amber-400">
              Model listing degraded. Manual model entry is available.
            </p>
          )}
          {availableModels.length > 0 && (
            <div className="mt-3 max-w-xs space-y-1.5">
              <label
                htmlFor={`provider-model-${provider.id}`}
                className="block text-xs font-medium text-neutral-400"
              >
                Model for {provider.displayName}
              </label>
              <select
                id={`provider-model-${provider.id}`}
                value={selectedModelValue}
                onChange={(event) => setSelectedModel(event.target.value)}
                className="w-full rounded-forge border border-surface-border bg-surface-bg px-2 py-1.5 font-mono text-xs text-white outline-none focus:border-forge-500"
              >
                {availableModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.displayName || model.id}
                  </option>
                ))}
              </select>
            </div>
          )}
          {models?.manualEntryAllowed && availableModels.length === 0 && (
            <div className="mt-3 max-w-xs space-y-1.5">
              <label
                htmlFor={`provider-manual-model-${provider.id}`}
                className="block text-xs font-medium text-neutral-400"
              >
                Manual model for {provider.displayName}
              </label>
              <input
                id={`provider-manual-model-${provider.id}`}
                type="text"
                value={manualModel}
                onChange={(event) => setManualModel(event.target.value)}
                className="w-full rounded-forge border border-surface-border bg-surface-bg px-2 py-1.5 font-mono text-xs text-white outline-none focus:border-forge-500"
              />
            </div>
          )}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button type="button" variant="secondary" size="sm" onClick={onLoadModels}>
            Models
          </Button>
          <Button type="button" variant="secondary" size="sm" isLoading={isTesting} onClick={() => onTest(modelForTest)}>
            Test Provider
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={onDelete}
            aria-label={`Delete Provider ${provider.displayName}`}
          >
            Delete
          </Button>
        </div>
      </div>
    </div>
  )
}

function APIKeySection() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<{
    provider: string
    api_key: string
    permission: ApiKeyPermission
  }>({ provider: 'kimi', api_key: '', permission: 'write' })
  const [isLoading, setIsLoading] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [keyPendingDelete, setKeyPendingDelete] = useState<ApiKey | null>(null)
  const [error, setError] = useState('')

  const loadKeys = useCallback(async () => {
    try {
      setKeys(await fetchApiKeys())
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '加载 API Key 失败'))
    }
  }, [])

  useEffect(() => {
    void Promise.resolve().then(loadKeys)
  }, [loadKeys])

  async function handleAdd() {
    setError('')
    if (!form.api_key.trim()) {
      setError('请输入 API Key')
      return
    }
    setIsLoading(true)
    try {
      await createApiKey({
        provider: form.provider,
        apiKey: form.api_key,
        permission: form.permission,
      })
      await loadKeys()
      setShowAdd(false)
      setForm({ provider: 'kimi', api_key: '', permission: 'write' })
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '添加 API Key 失败'))
    } finally {
      setIsLoading(false)
    }
  }

  async function confirmDelete() {
    if (!keyPendingDelete) return
    setError('')
    setIsDeleting(true)
    try {
      await deleteApiKey(keyPendingDelete.id)
      setKeys((prev) => prev.filter((k) => k.id !== keyPendingDelete.id))
      setKeyPendingDelete(null)
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, '删除 API Key 失败'))
    } finally {
      setIsDeleting(false)
    }
  }

  const providerLabel: Record<string, string> = {
    kimi: 'Kimi (Moonshot)',
    deepseek: 'DeepSeek',
  }
  const keyPendingDeleteLabel = keyPendingDelete
    ? providerLabel[keyPendingDelete.provider] || keyPendingDelete.provider
    : ''

  return (
    <section className="forge-card !bg-surface-dark space-y-4">
      <div className="flex items-center gap-2.5">
        <Key className="h-5 w-5 text-forge-400" />
        <h3 className="text-base font-semibold text-white">API 密钥管理</h3>
      </div>

      <p className="text-xs text-neutral-500">
        API Key 在服务器端加密存储，保存后仅显示掩码。
      </p>

      {error && !showAdd && !keyPendingDelete && (
        <p className="rounded-forge border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm text-red-400">
          {error}
        </p>
      )}

      {/* 已存 Key 列表 */}
      {keys.length > 0 ? (
        <div className="space-y-2">
          {keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-forge border border-surface-border px-4 py-3"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-white">
                  {providerLabel[key.provider] || key.provider}
                </p>
                <p className="text-xs text-neutral-400 font-mono">{key.maskedKey}</p>
                <p className="mt-0.5 text-[11px] text-neutral-500">
                  {key.permission} · 已用 {key.usageCount} 次
                </p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setError('')
                  setKeyPendingDelete(key)
                }}
                className="ml-3 shrink-0 rounded p-1.5 text-neutral-400 transition-colors hover:bg-red-500/10 hover:text-red-400"
                aria-label={`Delete API Key for ${providerLabel[key.provider] || key.provider}`}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-neutral-500">暂无存储的 API Key</p>
      )}

      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => {
          setError('')
          setShowAdd(true)
        }}
        leftIcon={<Plus className="h-4 w-4" />}
      >
        添加 API Key
      </Button>

      {/* 添加 Key 模态框 */}
      <Modal
        isOpen={showAdd}
        onClose={() => { setShowAdd(false); setError('') }}
        title="添加 API Key"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">提供商</label>
            <select
              value={form.provider}
              onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
              className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 text-sm text-white outline-none focus:border-forge-500"
            >
              <option value="kimi">Kimi (Moonshot)</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">API Key</label>
            <input
              type="password"
              value={form.api_key}
              onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
              placeholder="sk-..."
              className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 text-sm text-white font-mono placeholder-neutral-500 outline-none focus:border-forge-500"
            />
            <p className="mt-1 text-[11px] text-neutral-500">
              API Key 在服务器端加密存储，保存后仅显示掩码。
            </p>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-neutral-300">权限</label>
            <select
              value={form.permission}
              onChange={(e) => setForm((f) => ({ ...f, permission: e.target.value as ApiKeyPermission }))}
              className="w-full rounded-forge border border-surface-border bg-surface-bg px-3 py-2 text-sm text-white outline-none focus:border-forge-500"
            >
              <option value="write">write — 可用于 LLM 调用</option>
              <option value="read">read — 仅查看</option>
              <option value="admin">admin — 可管理</option>
            </select>
          </div>

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <Button type="button" variant="secondary" onClick={() => { setShowAdd(false); setError('') }}>
              取消
            </Button>
            <Button type="button" variant="primary" onClick={handleAdd} isLoading={isLoading}>
              保存
            </Button>
          </div>
        </div>
      </Modal>

      <Modal
        isOpen={keyPendingDelete !== null}
        onClose={() => { setKeyPendingDelete(null); setError('') }}
        title="删除 API Key"
        description={`确认删除 ${keyPendingDeleteLabel} 的 API Key？关联的 Provider 可能无法继续调用。`}
        size="sm"
      >
        <div className="space-y-4">
          {keyPendingDelete && (
            <div className="rounded-forge border border-surface-border bg-white/[0.02] px-4 py-3">
              <p className="text-sm font-medium text-white">{keyPendingDeleteLabel}</p>
              <p className="mt-1 font-mono text-xs text-neutral-400">{keyPendingDelete.maskedKey}</p>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-400">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => { setKeyPendingDelete(null); setError('') }}
            >
              取消
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={confirmDelete}
              isLoading={isDeleting}
            >
              确认删除
            </Button>
          </div>
        </div>
      </Modal>
    </section>
  )
}
