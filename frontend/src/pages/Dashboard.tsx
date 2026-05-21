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
} from 'lucide-react'
import { useTaskStore, STATUS_COLORS, STATUS_LABELS } from '../stores/taskStore'
import { useAgentStore, AGENT_STATUS_COLORS, AGENT_STATUS_LABELS } from '../stores/agentStore'
import TaskDurationChart from '../components/charts/TaskDurationChart'
import AgentCallsChart from '../components/charts/AgentCallsChart'
import apiClient from '../api/client'
import type { Task } from '../types'
import type { Agent } from '../types'

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

export default function Dashboard() {
  const navigate = useNavigate()
  const { tasks, isLoading: tasksLoading, fetchTasks } = useTaskStore()
  const { agents, isLoading: agentsLoading, fetchAgents, subscribeToAgents } = useAgentStore()

  // SSE 取消订阅函数引用
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    fetchTasks()
    fetchAgents()
    
    // 订阅 Agent 状态 SSE 实时更新
    unsubscribeRef.current = subscribeToAgents()

    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
    }
  }, [fetchTasks, fetchAgents, subscribeToAgents])

  const totalTasks = tasks.length
  const runningTasks = tasks.filter((t: Task) => t.status === 'running').length
  const completedTasks = tasks.filter((t: Task) => t.status === 'completed').length
  const statValues = { total: totalTasks, running: runningTasks, completed: completedTasks }

  const recentAgents = agents.slice(0, 4)

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

function DashboardCharts() {
  const [taskMetrics, setTaskMetrics] = useState<{ time: string; duration: number; count: number }[]>([])
  const [agentMetrics, setAgentMetrics] = useState<{ name: string; calls: number; avgDuration: number }[]>([])
  const [sysMetrics, setSysMetrics] = useState({ cpuUsage: 0, memoryUsage: 0, activeTasks: 0, totalRequests: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchMetrics() {
      try {
        const [taskRes, agentRes, sysRes] = await Promise.all([
          apiClient.get('/metrics/tasks?range_hours=24'),
          apiClient.get('/metrics/agents'),
          apiClient.get('/metrics/system'),
        ])

        // 任务指标
        const td = taskRes.data as { timestamps: string[]; durations: number[]; counts: number[] }
        setTaskMetrics(
          td.timestamps.map((t, i) => ({
            time: t,
            duration: td.durations[i] || 0,
            count: td.counts[i] || 0,
          }))
        )

        // Agent 指标
        const ad = (agentRes.data?.data || agentRes.data) as { name: string; calls: number; avgDuration: number }[]
        if (Array.isArray(ad)) {
          setAgentMetrics(ad)
        }

        // 系统指标
        const sd = sysRes.data as { cpuUsage: number; memoryUsage: number; activeTasks: number; totalRequests: number }
        setSysMetrics(sd)
      } catch (err) {
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

function SystemPanel({ metrics, loading }: { metrics: { cpuUsage: number; memoryUsage: number; activeTasks: number; totalRequests: number }; loading: boolean }) {
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
