/**
 * 全局测试 Setup
 *
 * - 导入 @testing-library/jest-dom 扩展断言
 * - Mock framer-motion 避免动画相关测试问题
 * - Mock reactflow 避免 DOM 相关测试问题
 */
import '@testing-library/jest-dom'
import { vi } from 'vitest'
import type { ReactNode } from 'react'

type MockProps = Record<string, unknown>

// Mock framer-motion — 替换为普通 HTML 元素，方便断言
vi.mock('framer-motion', () => {
  const Actual = vi.importActual('framer-motion')
  return {
    ...Actual,
    motion: {
      div: 'div',
      button: 'button',
      span: 'span',
      p: 'p',
    },
    AnimatePresence: ({ children }: { children: ReactNode }) => children,
  }
})

// Mock reactflow — 流程图测试不需要真实 DOM 渲染
vi.mock('reactflow', async () => {
  return {
    default: () => null,
    ReactFlow: () => null,
    Handle: () => null,
    Position: { Top: 'top', Bottom: 'bottom', Left: 'left', Right: 'right' },
    Background: () => null,
    Controls: () => null,
    MiniMap: () => null,
    useNodesState: () => [[], vi.fn()],
    useEdgesState: () => [[], vi.fn()],
    useReactFlow: () => ({}),
  }
})

// Mock lucide-react — 拦截所有图标导入
vi.mock('lucide-react', async () => {
  const React = await import('react')
  const mock: Record<string, unknown> = { __esModule: true }
  
  // 处理已知图标
  const icons = [
    'X', 'CheckCircle2', 'AlertCircle', 'AlertTriangle', 'Info',
    'Plus', 'Trash2', 'Key', 'Moon', 'Sun', 'Monitor', 'Bot',
    'Loader2', 'Eye', 'EyeOff', 'LogIn', 'UserPlus',
    'ArrowRight', 'ArrowLeft', 'ListTodo', 'Circle', 'CirclePlay', 'CircleCheck',
    'TrendingUp', 'BarChart3', 'Clock', 'Network', 'List',
    'RefreshCw', 'Cpu', 'HardDrive', 'Wifi', 'WifiOff', 'Search', 'Brain',
    'Zap', 'MessageSquare', 'Wrench', 'Shield', 'User', 'Mail',
    'Lock', 'Save', 'RotateCcw', 'LogOut', 'Send', 'Sliders', 'Play',
  ]
  
  for (const name of icons) {
    mock[name] = (props: MockProps) => (
      React.createElement('span', { 'data-icon': name.toLowerCase(), ...props })
    )
  }
  
  return mock
})

// Mock recharts（性能图表测试不需要完整渲染）
vi.mock('recharts', async () => {
  const React = await import('react')
  return {
    LineChart: ({ children }: { children?: ReactNode }) => (
      React.createElement('div', null, children)
    ),
    BarChart: ({ children }: { children?: ReactNode }) => (
      React.createElement('div', null, children)
    ),
    Line: () => null,
    Bar: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    ResponsiveContainer: ({ children }: { children?: ReactNode }) => (
      React.createElement('div', null, children)
    ),
  }
})
