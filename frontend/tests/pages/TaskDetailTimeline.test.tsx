import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TaskDetail from '../../src/pages/TaskDetail'

const storeMocks = vi.hoisted(() => ({
  taskState: {
    currentTask: {
      id: 'task-1',
      title: 'Plan release',
      description: 'Prepare a release plan',
      status: 'executing',
      priority: 'medium',
      assignedAgents: ['agent-coder'],
      dependencies: [],
      createdAt: '2026-06-26T01:00:00Z',
      updatedAt: '2026-06-26T01:05:00Z',
    },
    steps: [
      {
        id: 'step-3',
        taskId: 'task-1',
        order: 3,
        action: 'Review final output',
        stepType: 'final',
        status: 'pending',
        agentId: 'agent-reviewer',
      },
    ],
    isLoading: false,
    error: null as string | null,
    streamStatus: 'connected',
    fetchTaskDetail: vi.fn().mockResolvedValue(undefined),
    subscribeToTask: vi.fn(() => vi.fn()),
    clearError: vi.fn(),
  },
}))

vi.mock('../../src/stores/taskStore', () => ({
  useTaskStore: () => storeMocks.taskState,
  STATUS_COLORS: {
    pending: 'pending',
    planning: 'planning',
    executing: 'executing',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
  },
  STATUS_LABELS: {
    pending: 'pending',
    planning: 'planning',
    executing: 'executing',
    completed: 'completed',
    failed: 'failed',
    cancelled: 'cancelled',
  },
  STEP_TYPE_COLORS: {
    thought: 'thought',
    action: 'action',
    observation: 'observation',
    final: 'final',
    error: 'error',
  },
  STEP_TYPE_LABELS: {
    thought: 'thought',
    action: 'action',
    observation: 'observation',
    final: 'final',
    error: 'error',
  },
}))

function renderTaskDetail() {
  render(
    <MemoryRouter initialEntries={['/tasks/task-1']}>
      <Routes>
        <Route path="/tasks/:id" element={<TaskDetail />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('TaskDetail timeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the stable Step order instead of the visible array index', () => {
    renderTaskDetail()

    expect(screen.getByText('#03')).toBeInTheDocument()
    expect(screen.queryByText('#01')).not.toBeInTheDocument()
  })

  it('shows the Task stream connection status', () => {
    renderTaskDetail()

    expect(screen.getByText('SSE connected')).toBeInTheDocument()
  })

  it('renders error Step result as a local alert with Agent context', () => {
    storeMocks.taskState.steps = [
      {
        id: 'step-error',
        taskId: 'task-1',
        order: 4,
        action: 'Provider call failed',
        stepType: 'error',
        status: 'failed',
        result: 'Provider timeout',
        agentId: 'agent-reviewer',
      },
    ]

    renderTaskDetail()

    const alert = screen.getByRole('alert')
    expect(within(alert).getByText('Provider timeout')).toBeInTheDocument()
    expect(screen.getByText('agent-reviewer')).toBeInTheDocument()
  })
})
