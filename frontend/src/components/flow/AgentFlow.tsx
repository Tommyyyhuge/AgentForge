import { useCallback, useMemo } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type ReactFlowInstance,
} from 'reactflow'
import 'reactflow/dist/style.css'
import type { Task, Agent } from '../../types'
import type { FlowNode, FlowEdge } from '../../types/flow'
import AgentNode from './AgentNode'

// 自定义节点类型
const nodeTypes = {
  agent: AgentNode,
}

interface AgentFlowProps {
  /** 任务数据（用于生成 DAG） */
  task?: Task
  /** Agent 列表 */
  agents: Agent[]
  /** 是否可交互 */
  interactive?: boolean
  /** 高度 */
  height?: string
}

/**
 * Agent 协作流程图
 *
 * 从任务的 assignedAgents 和依赖关系生成 DAG 图
 */
export default function AgentFlow({
  task,
  agents,
  interactive = true,
  height = '400px',
}: AgentFlowProps) {
  // 生成节点和边
  const { initialNodes, initialEdges } = useMemo(() => {
    if (!task) {
      // 无任务时，显示所有 Agent 的扁平列表
      const nodes: FlowNode[] = agents.map((agent, index) => ({
        id: agent.id,
        type: 'agent',
        position: { x: index * 200 + 50, y: 100 },
        data: {
          id: agent.id,
          name: agent.name,
          role: agent.role,
          status: agent.status,
          description: agent.description,
          model: agent.model,
        },
      }))

      return { initialNodes: nodes, initialEdges: [] as FlowEdge[] }
    }

    // 根据任务的 assignedAgents 生成 DAG
    const assignedAgentIds = task.assignedAgents || []
    const assignedAgents = agents.filter((a) => assignedAgentIds.includes(a.id))

    // 简单的分层布局
    const nodes: FlowNode[] = assignedAgents.map((agent, index) => ({
      id: agent.id,
      type: 'agent',
      position: { x: index * 220 + 50, y: 100 },
      data: {
        id: agent.id,
        name: agent.name,
        role: agent.role,
        status: agent.status,
        description: agent.description,
        model: agent.model,
      },
    }))

    // 生成边（基于依赖关系或默认顺序）
    const edges: FlowEdge[] = []
    for (let i = 0; i < assignedAgents.length - 1; i++) {
      edges.push({
        id: `e-${assignedAgents[i].id}-${assignedAgents[i + 1].id}`,
        source: assignedAgents[i].id,
        target: assignedAgents[i + 1].id,
        type: 'default',
        animated: assignedAgents[i].status === 'busy',
      })
    }

    return { initialNodes: nodes, initialEdges: edges }
  }, [task, agents])

  const [nodes, , onNodesChange] = useNodesState(initialNodes as Node[])
  const [edges, , onEdgesChange] = useEdgesState(initialEdges as Edge[])

  const onInit = useCallback((instance: ReactFlowInstance) => {
    instance.fitView({ padding: 0.2 })
  }, [])

  return (
    <div style={{ height }} className="rounded-forge border border-surface-border">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onInit={onInit}
        fitView
        attributionPosition="bottom-left"
        nodesDraggable={interactive}
        nodesConnectable={false}
        elementsSelectable={interactive}
        zoomOnDoubleClick={interactive}
        panOnDrag={interactive}
      >
        <Background color="#525252" gap={16} size={1} />
        <Controls className="!border-surface-border !bg-surface-light" />
        <MiniMap
          className="!border-surface-border !bg-surface-light"
          nodeColor={(node) => {
            const data = node.data as { status?: string } | undefined
            switch (data?.status) {
              case 'executing':
                return '#f59e0b'
              case 'completed':
                return '#10b981'
              case 'error':
                return '#ef4444'
              default:
                return '#525252'
            }
          }}
          maskColor="rgba(0, 0, 0, 0.3)"
        />
      </ReactFlow>
    </div>
  )
}
