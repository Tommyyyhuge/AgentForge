import type { AgentRole, AgentStatus } from '.'

// ============================================================
// 流程图节点类型
// ============================================================

export interface FlowNodeData {
  /** Agent ID */
  id: string
  /** Agent 名称 */
  name: string
  /** Agent 角色 */
  role: AgentRole
  /** 当前状态 */
  status: AgentStatus
  /** 描述 */
  description: string
  /** 使用的模型 */
  model: string
}

export interface FlowNode {
  id: string
  type: 'agent'
  position: { x: number; y: number }
  data: FlowNodeData
}

// ============================================================
// 流程图边类型
// ============================================================

export interface FlowEdge {
  id: string
  source: string
  target: string
  type?: 'default' | 'animated'
  animated?: boolean
  data?: {
    messageType?: 'assignment' | 'result' | 'feedback'
    label?: string
  }
}

// ============================================================
// 任务流程图数据
// ============================================================

export interface TaskFlowData {
  nodes: FlowNode[]
  edges: FlowEdge[]
}
