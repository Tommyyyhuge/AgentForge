import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

// 暗色主题图表配置
const darkTheme = {
  backgroundColor: 'transparent',
  textColor: '#a3a3a3',
  gridColor: '#262626',
  strokeColor: '#1a3fff',
}

interface DataPoint {
  time: string
  duration: number
  count: number
}

interface TaskDurationChartProps {
  data: DataPoint[]
}

/**
 * 任务执行时间趋势图
 */
function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (active && payload && payload.length) {
    return (
      <div className="rounded-forge border border-surface-border bg-surface-light px-3 py-2 shadow-forge">
        <p className="text-xs text-neutral-400">{label}</p>
        <p className="text-sm text-white">
          平均耗时: <span className="text-forge-400">{payload[0].value}ms</span>
        </p>
        <p className="text-sm text-white">
          任务数: <span className="text-emerald-400">{payload[1]?.value}</span>
        </p>
      </div>
    )
  }
  return null
}

export default function TaskDurationChart({ data }: TaskDurationChartProps) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={darkTheme.gridColor} />
          <XAxis
            dataKey="time"
            stroke={darkTheme.textColor}
            fontSize={12}
            tickLine={false}
          />
          <YAxis
            stroke={darkTheme.textColor}
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="duration"
            stroke="#1a3fff"
            strokeWidth={2}
            dot={{ fill: '#1a3fff', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, fill: '#4a72ff' }}
            name="平均耗时(ms)"
          />
          <Line
            type="monotone"
            dataKey="count"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, fill: '#34d399' }}
            name="任务数"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
