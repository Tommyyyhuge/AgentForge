import { useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Clock,
  User,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Circle,
  Play,
} from 'lucide-react'
import {
  useTaskStore,
  STATUS_COLORS,
  STATUS_LABELS,
  STEP_TYPE_COLORS,
  STEP_TYPE_LABELS,
} from '../stores/taskStore'


// 步骤状态图标
const STEP_STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  running:   <Loader2 className="h-4 w-4 animate-spin text-forge-400" />,
  failed:    <AlertCircle className="h-4 w-4 text-red-400" />,
  pending:   <Circle className="h-3.5 w-3.5 text-neutral-600" />,
}

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const {
    currentTask,
    steps,
    isLoading,
    error,
    fetchTaskDetail,
    subscribeToTask,
    clearError,
  } = useTaskStore()

  // SSE 取消订阅函数引用（组件卸载时调用）
  const unsubscribeRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!id) return

    // 1. 获取任务详情（含步骤）
    fetchTaskDetail(id).catch(() => {})

    // 2. 订阅 SSE 实时更新
    unsubscribeRef.current = subscribeToTask(id)

    // 3. 组件卸载时：清理 SSE 连接 + 清除错误状态
    return () => {
      unsubscribeRef.current?.()
      unsubscribeRef.current = null
      clearError()
    }
  }, [id, fetchTaskDetail, subscribeToTask, clearError])

  // 加载中
  if (isLoading && !currentTask) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-forge-400" />
      </div>
    )
  }

  // 错误状态
  if (error && !currentTask) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3 text-neutral-400">
        <AlertCircle className="h-10 w-10 text-red-400" />
        <p className="text-sm">{error}</p>
        <button onClick={() => navigate(-1)} className="forge-btn-ghost">
          返回
        </button>
      </div>
    )
  }

  if (!currentTask) return null

  return (
    <div className="mx-auto max-w-4xl space-y-6 animate-slide-up">
      {/* 返回按钮 */}
      <button
        onClick={() => navigate('/tasks')}
        className="forge-btn-ghost inline-flex items-center gap-2"
      >
        <ArrowLeft className="h-4 w-4" />
        返回任务列表
      </button>

      {/* 任务信息卡片 */}
      <div className="forge-card !bg-surface-dark space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <h2 className="text-xl font-bold text-white">{currentTask.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-neutral-400">
              {currentTask.description || '暂无描述'}
            </p>
          </div>
          <span className={`forge-badge shrink-0 border self-start ${STATUS_COLORS[currentTask.status]}`}>
            {STATUS_LABELS[currentTask.status]}
          </span>
        </div>

        {/* 元数据行 */}
        <div className="flex flex-wrap gap-4 text-xs text-neutral-500">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            创建：{new Date(currentTask.createdAt).toLocaleString('zh-CN')}
          </div>
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            更新：{new Date(currentTask.updatedAt).toLocaleString('zh-CN')}
          </div>
          {currentTask.completedAt && (
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              完成：{new Date(currentTask.completedAt).toLocaleString('zh-CN')}
            </div>
          )}
        </div>

        {/* Agent 标签 */}
        {currentTask.assignedAgents.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <User className="h-3.5 w-3.5 text-neutral-500" />
            {currentTask.assignedAgents.map((agentId: string) => (
              <span
                key={agentId}
                className="rounded-full border border-forge-500/20 bg-forge-500/10
                           px-2.5 py-0.5 text-xs text-forge-300"
              >
                {agentId}
              </span>
            ))}
          </div>
        )}

        {/* 错误信息 */}
        {currentTask.error && (
          <div className="flex items-start gap-2 rounded-forge border border-red-500/20
                          bg-red-500/5 p-3 text-sm text-red-400">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            {currentTask.error}
          </div>
        )}
      </div>

      {/* 执行步骤时间线 */}
      <div className="forge-card !bg-surface-dark">
        <h3 className="mb-5 flex items-center gap-2 text-base font-semibold text-white">
          <Play className="h-5 w-5 text-forge-400" />
          执行步骤
        </h3>

        {steps.length === 0 ? (
          <p className="py-8 text-center text-sm text-neutral-500">暂无执行步骤</p>
        ) : (
          <div className="relative">
            {/* 时间线竖线 */}
            <div className="absolute left-[19px] top-2 bottom-2 w-px bg-surface-border" />

            <div className="space-y-5">
              {steps.map((step, idx) => (
                <StepItem key={step.id} step={step} index={idx} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// 单个步骤项
function StepItem({ step, index }: { step: import('../stores/taskStore').StepWithDisplay; index: number }) {
  const statusIcon = STEP_STATUS_ICON[step.status] ?? STEP_STATUS_ICON.pending
  const typeColor = STEP_TYPE_COLORS[step.stepType] ?? STEP_TYPE_COLORS.action
  const typeLabel = STEP_TYPE_LABELS[step.stepType] ?? step.stepType

  return (
    <div className="relative flex gap-4">
      {/* 左侧图标区 */}
      <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center
                      rounded-full bg-surface-dark ring-1 ring-surface-border">
        {statusIcon}
      </div>

      {/* 右侧内容 */}
      <div className="flex-1 min-w-0 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-neutral-500 tabular-nums">
            #{String(index + 1).padStart(2, '0')}
          </span>
          <span className={`forge-badge border ${typeColor}`}>
            {typeLabel}
          </span>
          {step.agentId && (
            <span className="text-xs text-neutral-600">{step.agentId}</span>
          )}
        </div>

        <p className="mt-1.5 text-sm leading-relaxed text-neutral-200">
          {step.action}
        </p>

        {step.result && (
          <div className="mt-2 rounded-forge border border-surface-border
                          bg-white/[0.02] p-3">
            <p className="text-xs leading-relaxed text-neutral-400">
              {step.result}
            </p>
          </div>
        )}

        {/* 时间 */}
        {step.startedAt && (
          <p className="mt-1.5 text-xs text-neutral-600">
            {new Date(step.startedAt).toLocaleString('zh-CN')}
            {step.completedAt &&
              ` → ${new Date(step.completedAt).toLocaleString('zh-CN')}`}
          </p>
        )}
      </div>
    </div>
  )
}
