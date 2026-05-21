import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ListTodo,
  CirclePlay,
  CircleCheck,
  Plus,
  Bot,
  ArrowRight,
  TrendingUp,
} from 'lucide-react'
import { useTaskStore, STATUS_COLORS, STATUS_LABELS } from '../stores/taskStore'
import { useAgentStore, AGENT_STATUS_COLORS, AGENT_STATUS_LABELS } from '../stores/agentStore'
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
