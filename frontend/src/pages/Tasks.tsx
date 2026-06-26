import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, List } from 'lucide-react'
import { useTaskStore, STATUS_COLORS, STATUS_LABELS } from '../stores/taskStore'
import type { TaskStatus } from '../types'

export default function Tasks() {
  const navigate = useNavigate()
  const { tasks, isLoading, fetchTasks } = useTaskStore()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all')

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const filtered = tasks.filter((task) => {
    const matchSearch =
      !search ||
      task.title.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || task.status === statusFilter
    return matchSearch && matchStatus
  })

  const statuses: Array<TaskStatus | 'all'> = [
    'all', 'pending', 'planning', 'executing', 'completed', 'failed', 'cancelled',
  ]

  return (
    <div className="mx-auto max-w-6xl space-y-6 animate-slide-up">
      {/* 标题栏 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">任务管理</h2>
          <p className="mt-1 text-sm text-neutral-400">
            共 {tasks.length} 个任务
          </p>
        </div>

        <button
          onClick={() => {
            // 预留：弹出创建任务对话框
            useTaskStore.getState().createTask({
              title: '新任务',
              priority: 'medium',
            }).then(() => fetchTasks())
          }}
          className="forge-btn-primary flex items-center gap-2 self-start"
        >
          <Plus className="h-4 w-4" />
          创建任务
        </button>
      </div>

      {/* 搜索 & 筛选 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4
                              -translate-y-1/2 text-neutral-500" />
          <input
            type="text"
            placeholder="搜索任务..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-forge border border-surface-border
                       bg-surface-dark py-2 pl-9 pr-3 text-sm text-white
                       placeholder:text-neutral-600
                       outline-none transition-colors
                       focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors
                ${statusFilter === s
                  ? 'bg-forge-500/15 text-forge-300 ring-1 ring-forge-500/20'
                  : 'text-neutral-500 hover:text-neutral-300 hover:bg-white/5'
                }
              `}
            >
              {s === 'all' ? '全部' : STATUS_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      {/* 任务表格 */}
      <div className="forge-card !bg-surface-dark !p-0 overflow-hidden">
        {isLoading ? (
          <div className="space-y-3 p-6">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-12 animate-pulse rounded-forge bg-white/5" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-neutral-500">
            <List className="mb-3 h-10 w-10 opacity-30" />
            <p className="text-sm">
              {search || statusFilter !== 'all' ? '没有匹配的任务' : '暂无任务'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="px-6 py-3 font-medium text-neutral-400">标题</th>
                  <th className="px-6 py-3 font-medium text-neutral-400 hidden sm:table-cell">
                    状态
                  </th>
                  <th className="px-6 py-3 font-medium text-neutral-400 hidden md:table-cell">
                    优先级
                  </th>
                  <th className="px-6 py-3 font-medium text-neutral-400 hidden lg:table-cell">
                    创建时间
                  </th>
                  <th className="px-6 py-3 font-medium text-neutral-400 hidden lg:table-cell">
                    更新时间
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {filtered.map((task) => (
                  <tr
                    key={task.id}
                    onClick={() => navigate(`/tasks/${task.id}`)}
                    className="cursor-pointer transition-colors hover:bg-white/[0.02]"
                  >
                    {/* 标题 */}
                    <td className="px-6 py-3.5">
                      <div>
                        <p className="font-medium text-white text-truncate max-w-[200px] sm:max-w-[300px]">
                          {task.title}
                        </p>
                        {/* 移动端显示状态 */}
                        <span
                          className={`forge-badge mt-1 border sm:hidden ${STATUS_COLORS[task.status]}`}
                        >
                          {STATUS_LABELS[task.status]}
                        </span>
                      </div>
                    </td>
                    {/* 状态 */}
                    <td className="px-6 py-3.5 hidden sm:table-cell">
                      <span className={`forge-badge border ${STATUS_COLORS[task.status]}`}>
                        {STATUS_LABELS[task.status]}
                      </span>
                    </td>
                    {/* 优先级 */}
                    <td className="px-6 py-3.5 hidden md:table-cell">
                      <PriorityBadge priority={task.priority} />
                    </td>
                    {/* 创建时间 */}
                    <td className="px-6 py-3.5 text-neutral-400 hidden lg:table-cell">
                      {new Date(task.createdAt).toLocaleString('zh-CN')}
                    </td>
                    {/* 更新时间 */}
                    <td className="px-6 py-3.5 text-neutral-400 hidden lg:table-cell">
                      {new Date(task.updatedAt).toLocaleString('zh-CN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

// 优先级徽章
const PRIORITY_CONFIG = {
  low:      { label: '低', cls: 'bg-slate-500/10 text-slate-400 border-slate-500/20' },
  medium:   { label: '中', cls: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
  high:     { label: '高', cls: 'bg-orange-500/10 text-orange-400 border-orange-500/20' },
  critical: { label: '紧急', cls: 'bg-red-500/10 text-red-400 border-red-500/20' },
}

function PriorityBadge({ priority }: { priority: string }) {
  const cfg = PRIORITY_CONFIG[priority as keyof typeof PRIORITY_CONFIG]
  if (!cfg) return <span className="text-xs text-neutral-500">-</span>
  return (
    <span className={`forge-badge border ${cfg.cls}`}>
      {cfg.label}
    </span>
  )
}
