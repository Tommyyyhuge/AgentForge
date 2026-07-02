import { type ReactNode, memo } from 'react'
import { type AgentStatus } from '../../types'
import { AGENT_STATUS_COLORS, AGENT_STATUS_LABELS } from '../../stores/agentStore'

interface BadgeProps {
  status: AgentStatus
  label?: string
  size?: 'sm' | 'md'
  children?: ReactNode
}

const sizeClasses = {
  sm: 'px-2 py-0 text-[11px]',
  md: 'px-2.5 py-0.5 text-xs',
} as const

function Badge({ status, label, size = 'md', children }: BadgeProps) {
  const colorClass = AGENT_STATUS_COLORS[status] ?? 'bg-semantic-idle/10 text-semantic-idle border-semantic-idle/20'
  const displayLabel = label ?? AGENT_STATUS_LABELS[status] ?? status

  return (
    <span className={`forge-badge border ${colorClass} ${sizeClasses[size]}`}>
      {children ?? displayLabel}
    </span>
  )
}

export default memo(Badge)
