import { useEffect, useRef, useState } from 'react'
import {
  Bot,
  RefreshCw,
  Clock,
  Cpu,
  Wifi,
  WifiOff,
  Network,
  List,
} from 'lucide-react'
import { useAgentStore, AGENT_STATUS_COLORS, AGENT_ROLE_LABELS } from '../stores/agentStore'
import Badge from '../components/ui/Badge'
import AgentFlow from '../components/flow/AgentFlow'
import type { Agent } from '../types'

/** Agent 角色图标映射 */
const ROLE_ICONS: Record<string, React.ReactNode> = {
  researcher:    <Bot className="h-4 w-4 text-emerald-400" />,
  coder:         <Bot className="h-4 w-4 text-cyan-400" />,
  writer:        <Bot className="h-4 w-4 text-brand-primary" />,
  reviewer:      <Bot className="h-4 w-4 text-semantic-executing" />,
  executor:      <Bot className="h-4 w-4 text-amber-400" />,
}

/** 格式化为多久之前 */
function timeAgo(dateStr: string): string {
  const now = Date.now()
  const past = new Date(dateStr).getTime()
  const diffSec = Math.floor((now - past) / 1000)
  if (diffSec < 60) return '刚刚'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} 分钟前`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} 小时前`
  return `${Math.floor(diffSec / 86400)} 天前`
}

export default function AgentMonitor() {
  const { agents, isLoading, error, fetchAgents, subscribeToAgents } = useAgentStore()
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    fetchAgents()
    unsubscribeRef.current = subscribeToAgents()
    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
    }
  }, [fetchAgents, subscribeToAgents])

  const onlineCount = agents.filter((a) => a.status !== 'error').length
  const busyCount = agents.filter((a) => a.status === 'busy').length

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-slide-up">
      {/* 标题栏 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Agent 监控</h2>
          <p className="mt-1 text-sm text-neutral-400">
            实时监控所有 Agent 的运行状态
          </p>
        </div>

        <button
          onClick={() => fetchAgents()}
          className="forge-btn-ghost inline-flex items-center gap-2 self-start"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      {/* 状态概览 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div className="forge-card !bg-surface-dark flex items-center gap-3 !p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-forge bg-forge-500/10">
            <Bot className="h-5 w-5 text-forge-400" />
          </div>
          <div>
            <p className="text-xs text-neutral-500">Agent 总数</p>
            <p className="text-lg font-semibold text-white">{agents.length}</p>
          </div>
        </div>

        <div className="forge-card !bg-surface-dark flex items-center gap-3 !p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-forge bg-emerald-500/10">
            <Wifi className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-neutral-500">在线</p>
            <p className="text-lg font-semibold text-white">{onlineCount}</p>
          </div>
        </div>

        <div className="forge-card !bg-surface-dark flex items-center gap-3 !p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-forge bg-amber-500/10">
            <Cpu className="h-5 w-5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs text-neutral-500">忙碌</p>
            <p className="text-lg font-semibold text-white">{busyCount}</p>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="flex items-center gap-2 rounded-forge border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          <WifiOff className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* 标签页切换 */}
      <AgentMonitorTabs agents={agents} isLoading={isLoading} />
    </div>
  )
}

// ============================================================
// 标签页组件
// ============================================================

type ViewMode = 'list' | 'flow'

function AgentMonitorTabs({ agents, isLoading }: { agents: Agent[]; isLoading: boolean }) {
  const [viewMode, setViewMode] = useState<ViewMode>('list')

  return (
    <div className="space-y-4">
      {/* 标签页头部 */}
      <div className="flex items-center gap-1 border-b border-surface-border">
        <button
          onClick={() => setViewMode('list')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            viewMode === 'list'
              ? 'border-forge-500 text-forge-400'
              : 'border-transparent text-neutral-400 hover:text-neutral-300'
          }`}
        >
          <List className="h-4 w-4" />
          列表视图
        </button>
        <button
          onClick={() => setViewMode('flow')}
          className={`flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
            viewMode === 'flow'
              ? 'border-forge-500 text-forge-400'
              : 'border-transparent text-neutral-400 hover:text-neutral-300'
          }`}
        >
          <Network className="h-4 w-4" />
          流程图
        </button>
      </div>

      {/* 内容区域 */}
      {viewMode === 'list' ? (
        <AgentListView agents={agents} isLoading={isLoading} />
      ) : (
        <AgentFlowView agents={agents} />
      )}
    </div>
  )
}

// ============================================================
// 列表视图
// ============================================================

function AgentListView({ agents, isLoading }: { agents: Agent[]; isLoading: boolean }) {
  if (agents.length === 0 && !isLoading) {
    return (
      <div className="flex h-48 items-center justify-center text-neutral-500">
        <p>暂无 Agent 数据</p>
      </div>
    )
  }

  return (
    <>
      {/* 桌面端表格 */}
      <div className="hidden overflow-hidden rounded-forge border border-surface-border sm:block">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-surface-border bg-white/[0.02]">
              <th className="px-4 py-3 font-medium text-neutral-400">Agent</th>
              <th className="px-4 py-3 font-medium text-neutral-400">角色</th>
              <th className="px-4 py-3 font-medium text-neutral-400">模型</th>
              <th className="px-4 py-3 font-medium text-neutral-400">状态</th>
              <th className="px-4 py-3 font-medium text-neutral-400">最近活跃</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {agents.map((agent: Agent) => (
              <tr key={agent.id} className="transition-colors hover:bg-white/[0.02]">
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-full ${AGENT_STATUS_COLORS[agent.status].split(' ')[0]}`}>
                      {ROLE_ICONS[agent.role] ?? <Bot className="h-4 w-4 text-neutral-400" />}
                    </div>
                    <div>
                      <p className="font-medium text-white">{agent.name}</p>
                      <p className="text-xs text-neutral-500 max-w-[160px] text-truncate">{agent.description}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3.5">
                  <span className="text-neutral-300">{AGENT_ROLE_LABELS[agent.role]}</span>
                </td>
                <td className="px-4 py-3.5">
                  <span className="rounded-full bg-white/5 px-2 py-0.5 text-xs text-neutral-400 font-mono">{agent.model}</span>
                </td>
                <td className="px-4 py-3.5">
                  <Badge status={agent.status} />
                </td>
                <td className="px-4 py-3.5">
                  <div className="flex items-center gap-1.5 text-neutral-500">
                    <Clock className="h-3.5 w-3.5" />
                    <span>{timeAgo(agent.updatedAt)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 移动端卡片 */}
      <div className="flex flex-col gap-3 sm:hidden">
        {agents.map((agent: Agent) => (
          <div key={agent.id} className="forge-card !bg-surface-dark space-y-3 !p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-full ${AGENT_STATUS_COLORS[agent.status].split(' ')[0]}`}>
                  {ROLE_ICONS[agent.role] ?? <Bot className="h-5 w-5 text-neutral-400" />}
                </div>
                <div>
                  <p className="font-medium text-white">{agent.name}</p>
                  <p className="text-xs text-neutral-500">{AGENT_ROLE_LABELS[agent.role]}</p>
                </div>
              </div>
              <Badge status={agent.status} size="sm" />
            </div>
            <p className="text-xs text-neutral-500">{agent.description}</p>
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-500 font-mono">{agent.model}</span>
              <span className="flex items-center gap-1 text-neutral-600">
                <Clock className="h-3 w-3" />
                {timeAgo(agent.updatedAt)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

// ============================================================
// 流程图视图
// ============================================================

function AgentFlowView({ agents }: { agents: Agent[] }) {
  if (agents.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center rounded-forge border border-surface-border text-neutral-500">
        <p>暂无 Agent 数据</p>
      </div>
    )
  }

  return <AgentFlow agents={agents} height="500px" />
}
