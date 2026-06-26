import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useTaskStore } from '../../src/stores/taskStore'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  createSSEConnection: vi.fn(),
}))

vi.mock('../../src/api/client', () => ({
  default: {
    get: mocks.get,
    post: mocks.post,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  createSSEConnection: mocks.createSSEConnection,
}))

describe('taskStore API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useTaskStore.setState({
      tasks: [],
      currentTask: null,
      steps: [],
      isLoading: false,
      error: null,
    })
  })

  it('normalizes wrapped backend tasks into the UI task shape', async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        success: true,
        data: [
          {
            id: 'task-1',
            title: 'Plan',
            description: 'Plan the work',
            status: 'planning',
            created_at: '2026-06-26T01:00:00Z',
            updated_at: '2026-06-26T01:01:00Z',
          },
        ],
      },
    })

    await useTaskStore.getState().fetchTasks()

    expect(useTaskStore.getState().tasks[0]).toMatchObject({
      id: 'task-1',
      status: 'planning',
      priority: 'medium',
      assignedAgents: [],
      dependencies: [],
      createdAt: '2026-06-26T01:00:00Z',
      updatedAt: '2026-06-26T01:01:00Z',
    })
  })

  it('normalizes task SSE step and done events', () => {
    mocks.createSSEConnection.mockReturnValue({ close: vi.fn() })
    useTaskStore.setState({
      currentTask: {
        id: 'task-1',
        title: 'Plan',
        description: 'Plan the work',
        status: 'executing',
        priority: 'medium',
        assignedAgents: [],
        dependencies: [],
        createdAt: '2026-06-26T01:00:00Z',
        updatedAt: '2026-06-26T01:00:00Z',
      },
      tasks: [],
    })

    useTaskStore.getState().subscribeToTask('task-1')
    const config = mocks.createSSEConnection.mock.calls[0][1]

    config.onMessage({
      type: 'step_update',
      step: {
        id: 'step-1',
        task_id: 'task-1',
        agent_id: 'agent-researcher',
        step_number: 2,
        step_type: 'thought',
        content: 'Thinking',
        timestamp: '2026-06-26T01:02:00Z',
      },
    })
    config.onMessage({
      type: 'done',
      status: 'completed',
      task: {
        id: 'task-1',
        title: 'Plan',
        description: 'Plan the work',
        status: 'completed',
        created_at: '2026-06-26T01:00:00Z',
        updated_at: '2026-06-26T01:03:00Z',
      },
    })

    expect(useTaskStore.getState().steps[0]).toMatchObject({
      id: 'step-1',
      taskId: 'task-1',
      order: 2,
      action: 'Thinking',
      stepType: 'thought',
      status: 'completed',
      agentId: 'agent-researcher',
      startedAt: '2026-06-26T01:02:00Z',
    })
    expect(useTaskStore.getState().currentTask?.status).toBe('completed')
  })
})
