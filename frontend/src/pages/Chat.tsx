import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  Bot,
  ListTodo,
  Loader2,
  Plus,
  Send,
} from 'lucide-react'
import { useTaskStore } from '../stores/taskStore'

function buildTaskTitle(description: string): string {
  const firstLine = description.split('\n').find((line) => line.trim())?.trim() ?? 'New Task'
  return firstLine.length > 80 ? `${firstLine.slice(0, 77)}...` : firstLine
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : '创建 Task 失败'
}

export default function Chat() {
  const navigate = useNavigate()
  const { createTask } = useTaskStore()
  const [input, setInput] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [mobileShowList, setMobileShowList] = useState(true)

  const resetDraft = useCallback(() => {
    setInput('')
    setError('')
    setMobileShowList(false)
  }, [])

  const handleSubmit = useCallback(async () => {
    const description = input.trim()
    if (!description || isSubmitting) return

    setError('')
    setIsSubmitting(true)
    try {
      const task = await createTask({
        title: buildTaskTitle(description),
        description,
      })
      setInput('')
      navigate(`/tasks/${task.id}`)
    } catch (err: unknown) {
      setError(getErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }, [createTask, input, isSubmitting, navigate])

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-6xl gap-0 overflow-hidden rounded-forge border border-surface-border animate-slide-up">
      <aside
        className={`
          flex w-60 shrink-0 flex-col border-r border-surface-border bg-surface-dark
          ${mobileShowList ? 'flex' : 'hidden'}
          sm:flex
        `}
      >
        <div className="border-b border-surface-border p-3">
          <button
            type="button"
            onClick={resetDraft}
            className="forge-btn-primary flex w-full items-center justify-center gap-2 !py-2 text-sm"
          >
            <Plus className="h-4 w-4" />
            新 Task
          </button>
        </div>

        <div className="flex flex-1 items-center justify-center px-4 text-center">
          <div className="space-y-2">
            <ListTodo className="mx-auto h-8 w-8 text-neutral-600" />
            <p className="text-sm text-neutral-500">暂无 Chat 记录</p>
            <p className="text-xs text-neutral-600">Task 执行详情会显示真实 Step</p>
          </div>
        </div>
      </aside>

      <div className="flex flex-1 flex-col bg-surface-dark">
        {!mobileShowList && (
          <div className="flex items-center gap-2 border-b border-surface-border px-4 py-2 sm:hidden">
            <button
              type="button"
              onClick={() => setMobileShowList(true)}
              className="text-sm text-forge-400"
            >
              返回
            </button>
          </div>
        )}

        <div className="flex flex-1 items-center justify-center px-4 py-6">
          <div className="w-full max-w-2xl space-y-5">
            <div className="text-center">
              <Bot className="mx-auto h-12 w-12 text-neutral-600" />
              <h2 className="mt-3 text-lg font-semibold text-white">创建 Task</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Planner 和 Agent 会在 Task 执行页产生可观察的 Step。
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-center gap-2 rounded-forge border border-red-500/20 bg-red-500/5 px-3 py-2 text-sm text-red-400"
              >
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="space-y-2">
              <label htmlFor="chat-task-description" className="text-sm font-medium text-neutral-300">
                Task 描述
              </label>
              <textarea
                id="chat-task-description"
                value={input}
                onChange={(event) => {
                  setInput(event.target.value)
                  if (error) setError('')
                }}
                placeholder="描述要创建的 Task..."
                rows={6}
                className="w-full resize-none rounded-forge border border-surface-border
                           bg-white/[0.03] px-3 py-2.5 text-sm text-white
                           placeholder:text-neutral-600
                           outline-none transition-colors
                           focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!input.trim() || isSubmitting}
                aria-label="Create Task from Chat"
                className="forge-btn-primary inline-flex items-center gap-2 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
                创建 Task
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
