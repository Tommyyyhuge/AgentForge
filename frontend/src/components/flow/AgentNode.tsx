import { memo } from 'react'
import { Handle, Position, type NodeProps } from 'reactflow'
import { motion } from 'framer-motion'
import { Bot, Cpu, Brain, Wrench, Search, MessageSquare } from 'lucide-react'
import type { FlowNodeData } from '../../types/flow'
import { AGENT_STATUS_COLORS, AGENT_STATUS_LABELS, AGENT_ROLE_LABELS } from '../../stores/agentStore'

// 角色图标映射
const ROLE_ICONS: Record<string, React.ReactNode> = {
  orchestrator: <Cpu className="h-4 w-4" />,
  analyst: <Brain className="h-4 w-4" />,
  executor: <Wrench className="h-4 w-4" />,
  critic: <Bot className="h-4 w-4" />,
  researcher: <Search className="h-4 w-4" />,
  communicator: <MessageSquare className="h-4 w-4" />,
}

/**
 * 自定义 Agent 节点
 *
 * 特性：
 * - 显示 Agent 名称、角色、状态
 * - 状态变化时有动画
 * - 支持暗色主题
 */
const AgentNode = memo(({ data }: NodeProps<FlowNodeData>) => {
  const statusColor = AGENT_STATUS_COLORS[data.status]
  const statusLabel = AGENT_STATUS_LABELS[data.status]
  const roleLabel = AGENT_ROLE_LABELS[data.role]
  const icon = ROLE_ICONS[data.role] || <Bot className="h-4 w-4" />

  // 提取背景色和文字色
  const [bgClass = 'bg-semantic-idle/10'] = statusColor.split(' ')

  return (
    <motion.div
      className="min-w-[160px] rounded-forge border border-surface-border bg-surface-light p-3 shadow-forge"
      layout
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* 输入连接点 */}
      <Handle
        type="target"
        position={Position.Top}
        className="!h-3 !w-3 !border-2 !border-surface-border !bg-forge-500"
      />

      {/* 节点内容 */}
      <div className="flex items-center gap-2">
        <div className={`flex h-8 w-8 items-center justify-center rounded-full ${bgClass}`}>
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="truncate text-sm font-medium text-white">{data.name}</div>
          <div className="text-xs text-neutral-400">{roleLabel}</div>
        </div>
      </div>

      {/* 状态标签 */}
      <div className="mt-2 flex items-center justify-between">
        <span className={`inline-flex items-center rounded-forge px-2 py-0.5 text-[10px] font-medium ${statusColor}`}>
          {statusLabel}
        </span>
        <span className="text-[10px] text-neutral-500">{data.model}</span>
      </div>

      {/* 输出连接点 */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!h-3 !w-3 !border-2 !border-surface-border !bg-forge-500"
      />
    </motion.div>
  )
})

AgentNode.displayName = 'AgentNode'

export default AgentNode
