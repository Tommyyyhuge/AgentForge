import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface AgentCallData {
  name: string
  calls: number
  avgDuration: number
}

interface AgentCallsChartProps {
  data: AgentCallData[]
}

/**
 * Agent 调用分布图
 */
function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number; payload: { name: string; avgDuration: number } }> }) {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-forge border border-surface-border bg-surface-light px-3 py-2 shadow-forge">
        <p className="text-sm font-medium text-white">{payload[0].payload.name}</p>
        <p className="text-xs text-neutral-400">
          调用次数: <span className="text-forge-400">{payload[0].value}</span>
        </p>
        <p className="text-xs text-neutral-400">
          平均耗时: <span className="text-emerald-400">{payload[0].payload.avgDuration}ms</span>
        </p>
      </div>
    )
  }
  return null
}

export default function AgentCallsChart({ data }: AgentCallsChartProps) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
          <XAxis
            dataKey="name"
            stroke="#a3a3a3"
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke="#a3a3a3"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="calls"
            fill="#1a3fff"
            radius={[4, 4, 0, 0]}
            name="调用次数"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
