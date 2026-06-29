import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ListTodo,
  CirclePlay,
  CircleCheck,
  Plus,
  Bot,
  ArrowRight,
  TrendingUp,
  BarChart3,
  Clock,
  Cpu,
  HardDrive,
  AlertTriangle,
  CheckCircle2,
  Sliders,
} from 'lucide-react'
import { useTaskStore, STATUS_COLORS, STATUS_LABELS } from '../stores/taskStore'
import { useAgentStore, AGENT_STATUS_COLORS, AGENT_STATUS_LABELS } from '../stores/agentStore'
import { useProviderStore } from '../stores/providerStore'
import TaskDurationChart from '../components/charts/TaskDurationChart'
import AgentCallsChart from '../components/charts/AgentCallsChart'
import {
  fetchDashboardMetrics,
  type AgentMetric,
  type SystemMetrics,
  type TaskDurationMetric,
} from '../api/metrics'
import type { Agent, AgentStatus, ProviderConfig, ProviderHealthResult, Task } from '../types'

const STAT_CARDS = [
  {
    key: 'total',
    label: '总任务数',
    icon: ListTodo,
    color: 'text-forge-400',
    bg: 'bg-forge-500/10',
  },
  {
    key: 'running',
    label: '进行中',
    icon: CirclePlay,
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  {
    key: 'completed',
    label: '已完成',
    icon: CircleCheck,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
] as const

const AGENT_SUMMARY_STATUSES: AgentStatus[] = ['busy', 'idle', 'error']

export default function Dashboard() {
  const navigate = useNavigate()
  const { tasks, isLoading: tasksLoading, fetchTasks } = useTaskStore()
  const { agents, isLoading: agentsLoading, fetchAgents, subscribeToAgents } = useAgentStore()
  const {
    providers,
    healthByProviderId,
    isLoading: providersLoading,
    error: providerError,
    fetchProviderSettings,
  } = useProviderStore()

  // SSE 取消订阅函数引用
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    fetchTasks()
    fetchAgents()
    fetchProviderSettings()
    
    // 订阅 Agent 状态 SSE 实时更新
    unsubscribeRef.current = subscribeToAgents()

    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
    }
  }, [fetchTasks, fetchAgents, fetchProviderSettings, subscribeToAgents])

  const totalTasks = tasks.length
  const runningTasks = tasks.filter((t: Task) => t.status === 'executing').length
  const completedTasks = tasks.filter((t: Task) => t.status === 'completed').length
  const statValues = { total: totalTasks, running: runningTasks, completed: completedTasks }

  const recentAgents = agents.slice(0, 4)
  const agentStatusCounts = agents.reduce<Record<AgentStatus, number>>(
    (counts, agent) => {
      counts[agent.status] += 1
      return counts
    },
    { idle: 0, busy: 0, error: 0 },
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* 欢迎标题 */}
      <div className="animate-slide-up">
        <h2 className="text-2xl font-bold tracking-tight text-white lg:text-3xl">
          AgentForge 控制台
        </h2>
        <p className="mt-1 text-sm text-neutral-400">
          多 Agent 协作任务管理系统 — 概览
        </p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 animate-slide-up">
        {STAT_CARDS.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.key} className="forge-card flex items-center gap-4 !bg-surface-dark">
              <div className={`flex h-12 w-12 items-center justify-center rounded-forge ${card.bg}`}>
                <Icon className={`h-6 w-6 ${card.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-white tabular-nums">
                  {statValues[card.key]}
                </p>
                <p className="text-xs text-neutral-500">{card.label}</p>
              </div>
            </div>
          )
        })}
      </div>

      {/* 性能图表 */}
      <ProviderStatusPanel
        providers={providers}
        healthByProviderId={healthByProviderId}
        loading={providersLoading}
        error={providerError}
        onOpenSettings={() => navigate('/settings')}
      />

      <DashboardCharts />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* 快速操作 */}
        <div className="forge-card !bg-surface-dark lg:col-span-1 animate-scale-in">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-forge-400" />
            <h3 className="text-base font-semibold text-white">快速操作</h3>
          </div>

          <button
            onClick={() => navigate('/tasks')}
            className="forge-btn-primary mt-4 flex w-full items-center justify-center gap-2"
          >
            <Plus className="h-4 w-4" />
            创建任务
          </button>

          <div className="mt-4 space-y-2">
            <button
              onClick={() => navigate('/tasks')}
              className="forge-btn-ghost flex w-full items-center justify-between"
            >
              <span>查看所有任务</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Agent 状态列表 */}
        <div className="forge-card !bg-surface-dark lg:col-span-2 animate-scale-in">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-accent" />
            <h3 className="text-base font-semibold text-white">Agent 状态</h3>
          </div>

          {agentsLoading ? (
            <div className="mt-6 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-14 animate-pulse rounded-forge bg-white/5"
                />
              ))}
            </div>
          ) : (
            <>
              <div aria-label="Agent summary" className="mt-4">
                <p className="text-xs font-medium text-neutral-500">Agent summary</p>
                <div className="mt-2 grid grid-cols-3 gap-2">
                  {AGENT_SUMMARY_STATUSES.map((status) => (
                    <div
                      key={status}
                      className={`rounded-forge border px-3 py-2 ${AGENT_STATUS_COLORS[status]}`}
                    >
                      <p className="text-sm font-semibold tabular-nums">
                        {agentStatusCounts[status]} {status}
                      </p>
                      <p className="mt-0.5 text-xs opacity-80">
                        {AGENT_STATUS_LABELS[status]}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 divide-y divide-surface-border">
              {recentAgents.map((agent: Agent) => (
                <div
                  key={agent.id}
                  className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center
                                    rounded-forge bg-forge-500/10 text-forge-400
                                    text-sm font-semibold">
                      {agent.name[0]}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white text-truncate">
                        {agent.name}
                      </p>
                      <p className="text-xs text-neutral-500 text-truncate">
                        {agent.description}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`forge-badge shrink-0 border ${AGENT_STATUS_COLORS[agent.status]}`}
                  >
                    {AGENT_STATUS_LABELS[agent.status]}
                  </span>
                </div>
              ))}

              {recentAgents.length === 0 && (
                <p className="py-6 text-center text-sm text-neutral-500">
                  暂无 Agent
                </p>
              )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 最近任务 */}
      <div className="forge-card !bg-surface-dark animate-scale-in">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ListTodo className="h-5 w-5 text-forge-400" />
            <h3 className="text-base font-semibold text-white">最近任务</h3>
          </div>
          <button
            onClick={() => navigate('/tasks')}
            className="text-xs text-forge-400 transition-colors hover:text-forge-300"
          >
            查看全部 →
          </button>
        </div>

        {tasksLoading ? (
          <div className="mt-4 space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-forge bg-white/5" />
            ))}
          </div>
        ) : (
          <div className="mt-4 divide-y divide-surface-border">
            {tasks.slice(0, 5).map((task: Task) => (
              <div
                key={task.id}
                onClick={() => navigate(`/tasks/${task.id}`)}
                className="flex cursor-pointer items-center justify-between py-3
                           first:pt-0 last:pb-0 transition-colors hover:bg-white/[0.02]"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white text-truncate">
                    {task.title}
                  </p>
                  <p className="mt-0.5 text-xs text-neutral-500">
                    {new Date(task.createdAt).toLocaleDateString('zh-CN')}
                  </p>
                </div>
                <span
                  className={`forge-badge shrink-0 border ${STATUS_COLORS[task.status]}`}
                >
                  {STATUS_LABELS[task.status]}
                </span>
              </div>
            ))}

            {tasks.length === 0 && (
              <p className="py-6 text-center text-sm text-neutral-500">
                暂无任务，点击"创建任务"开始
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================
// 图表组件
// ============================================================

function ProviderStatusPanel({
  providers,
  healthByProviderId,
  loading,
  error,
  onOpenSettings,
}: {
  providers: ProviderConfig[]
  healthByProviderId: Record<string, ProviderHealthResult>
  loading: boolean
  error: string | null
  onOpenSettings: () => void
}) {
  const activeProviders = providers.filter((provider) => provider.isActive)
  const healthyProviders = activeProviders.filter(
    (provider) => healthByProviderId[provider.id]?.status === 'healthy',
  )
  const needsAttention = activeProviders.length === 0 || healthyProviders.length === 0 || Boolean(error)
  const attentionMessage = activeProviders.length === 0
    ? 'No active Provider is configured.'
    : error || 'No active healthy Provider is available.'
  const headline = needsAttention ? 'Provider attention required' : 'Providers ready'
  const Icon = needsAttention ? AlertTriangle : CheckCircle2

  return (
    <section
      className={`forge-card !bg-surface-dark animate-slide-up ${
        needsAttention ? 'border-amber-500/20' : 'border-emerald-500/20'
      }`}
      aria-live="polite"
    >
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <Icon className={`h-5 w-5 ${needsAttention ? 'text-amber-400' : 'text-emerald-400'}`} />
            <h3 className="text-base font-semibold text-white">{headline}</h3>
          </div>
          <p className="mt-1 text-sm text-neutral-400">
            {loading ? 'Loading Provider status...' : needsAttention ? attentionMessage : `${healthyProviders.length} active Provider`}
          </p>
          {activeProviders.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {activeProviders.slice(0, 4).map((provider) => {
                const health = healthByProviderId[provider.id]?.status ?? 'unknown'
                const isHealthy = health === 'healthy'
                return (
                  <span
                    key={provider.id}
                    className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs ${
                      isHealthy
                        ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                        : 'border-amber-500/20 bg-amber-500/10 text-amber-400'
                    }`}
                  >
                    <span>{provider.displayName}</span>
                    <span className="font-mono">{provider.defaultModel || provider.providerType}</span>
                    <span>{health}</span>
                  </span>
                )
              })}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onOpenSettings}
          className="forge-btn-secondary inline-flex shrink-0 items-center justify-center gap-2"
        >
          <Sliders className="h-4 w-4" />
          Provider Settings
        </button>
      </div>
    </section>
  )
}

function DashboardCharts() {
  const [taskMetrics, setTaskMetrics] = useState<TaskDurationMetric[]>([])
  const [agentMetrics, setAgentMetrics] = useState<AgentMetric[]>([])
  const [sysMetrics, setSysMetrics] = useState<SystemMetrics>({
    cpuUsage: 0,
    memoryUsage: 0,
    activeTasks: 0,
    totalRequests: 0,
  })
  const [loading, setLoading] = useState(true)
  const [metricsError, setMetricsError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchMetrics() {
      try {
        setMetricsError(null)
        const metrics = await fetchDashboardMetrics()

        // 任务指标
        setTaskMetrics(metrics.taskMetrics)

        // Agent 指标
        setAgentMetrics(metrics.agentMetrics)

        // 系统指标
        setSysMetrics(metrics.systemMetrics)
      } catch (err) {
        setMetricsError('Metrics unavailable')
        // 后端不可用时保持空数据，开发环境输出调试信息
        if (import.meta.env.DEV) {
          console.warn('[Dashboard] 指标数据获取失败:', err)
        }
      } finally {
        setLoading(false)
      }
    }
    fetchMetrics()
  }, [])

  return (
    <div className="space-y-6 animate-slide-up">
      {/* 系统资源面板 */}
      <SystemPanel metrics={sysMetrics} loading={loading} />

      {metricsError && (
        <div className="forge-card !bg-surface-dark border-red-500/20">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-400" />
            <h3 className="text-base font-semibold text-white">{metricsError}</h3>
          </div>
          <p className="mt-1 text-sm text-neutral-400">
            Metrics could not be loaded. Dashboard navigation remains available.
          </p>
        </div>
      )}

      {/* 图表 */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="forge-card !bg-surface-dark">
          <div className="mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-forge-400" />
            <h3 className="text-base font-semibold text-white">任务执行时间趋势</h3>
          </div>
          {loading ? (
            <div className="flex h-[300px] items-center justify-center text-neutral-500">加载中...</div>
          ) : (
            <TaskDurationChart data={taskMetrics} />
          )}
        </div>

        <div className="forge-card !bg-surface-dark">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-accent" />
            <h3 className="text-base font-semibold text-white">Agent 调用分布</h3>
          </div>
          {loading ? (
            <div className="flex h-[300px] items-center justify-center text-neutral-500">加载中...</div>
          ) : (
            <AgentCallsChart data={agentMetrics} />
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 系统资源面板
// ============================================================

function SystemPanel({ metrics, loading }: { metrics: SystemMetrics; loading: boolean }) {
  const items = [
    { label: 'CPU', value: metrics.cpuUsage, unit: '%', icon: Cpu, color: 'text-forge-400', barColor: 'bg-forge-500' },
    { label: '内存', value: metrics.memoryUsage, unit: '%', icon: HardDrive, color: 'text-amber-400', barColor: 'bg-amber-500' },
    { label: '活跃任务', value: metrics.activeTasks, unit: '', icon: CirclePlay, color: 'text-purple-400', barColor: 'bg-purple-500', max: 50 },
    { label: '总请求', value: metrics.totalRequests, unit: '', icon: TrendingUp, color: 'text-emerald-400', barColor: 'bg-emerald-500', max: 500 },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {items.map((item) => (
        <div key={item.label} className="forge-card !bg-surface-dark !p-4">
          <div className="mb-2 flex items-center gap-2">
            <item.icon className={`h-4 w-4 ${item.color}`} />
            <span className="text-xs text-neutral-400">{item.label}</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold text-white tabular-nums">
              {loading ? '—' : item.value}
            </span>
            {item.unit && <span className="text-xs text-neutral-500">{item.unit}</span>}
          </div>
          {/* 进度条 */}
          <div className="mt-2 h-1.5 rounded-full bg-neutral-700">
            <div
              className={`h-full rounded-full transition-all duration-500 ${item.barColor}`}
              style={{ width: `${Math.min((item.value / (item.max || 100)) * 100, 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
