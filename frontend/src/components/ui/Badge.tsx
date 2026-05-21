import { type ReactNode } from 'react'
import { type AgentStatus } from '../../types'
import { AGENT_STATUS_COLORS, AGENT_STATUS_LABELS } from '../../stores/agentStore'

interface BadgeProps {
  status: AgentStatus
  /** 自定义文本，默认使用状态标签 */
  label?: string
  /** 尺寸变体 */
  size?: 'sm' | 'md'
  children?: ReactNode
}

const sizeClasses = {
  sm: 'px-2 py-0 text-[11px]',
  md: 'px-2.5 py-0.5 text-xs',
} as const

export default function Badge({ status, label, size = 'md', children }: BadgeProps) {
  const colorClass = AGENT_STATUS_COLORS[status] ?? 'bg-slate-500/10 text-slate-400 border-slate-500/20'
  const displayLabel = label ?? AGENT_STATUS_LABELS[status] ?? status

  return (
    <span
      className={`forge-badge border ${colorClass} ${sizeClasses[size]}`}
    >
      {children ?? displayLabel}
    </span>
  )
}
