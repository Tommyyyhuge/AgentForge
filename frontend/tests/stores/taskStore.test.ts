import { beforeEach, describe, expect, it, vi } from 'vitest'
import { STEP_TYPE_COLORS, STEP_TYPE_LABELS, useTaskStore } from '../../src/stores/taskStore'

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
      streamStatus: 'disconnected',
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

  it('keeps Task list empty and reports an error when the backend is unavailable', async () => {
    mocks.get.mockRejectedValueOnce(new Error('无法连接到服务器，请确认后端已启动'))

    await useTaskStore.getState().fetchTasks()

    expect(useTaskStore.getState().tasks).toEqual([])
    expect(useTaskStore.getState().error).toBe('无法连接到服务器，请确认后端已启动')
  })

  it('does not create a local mock Task when task creation fails', async () => {
    const error = new Error('无法连接到服务器，请确认后端已启动')
    mocks.post.mockRejectedValueOnce(error)

    await expect(
      useTaskStore.getState().createTask({ title: 'Real backend task' }),
    ).rejects.toThrow('无法连接到服务器，请确认后端已启动')

    expect(useTaskStore.getState().tasks).toEqual([])
    expect(useTaskStore.getState().error).toBe('无法连接到服务器，请确认后端已启动')
  })

  it('does not synthesize Task detail when the backend is unavailable', async () => {
    mocks.get.mockRejectedValueOnce(new Error('无法连接到服务器，请确认后端已启动'))

    await expect(useTaskStore.getState().fetchTaskDetail('task-1')).rejects.toThrow(
      '无法连接到服务器，请确认后端已启动',
    )

    expect(useTaskStore.getState().currentTask).toBeNull()
    expect(useTaskStore.getState().steps).toEqual([])
    expect(useTaskStore.getState().error).toBe('无法连接到服务器，请确认后端已启动')
  })

  it('uses PRD Step type values as timeline labels and color keys', () => {
    const stepTypes = ['thought', 'action', 'observation', 'final', 'error'] as const

    expect(Object.keys(STEP_TYPE_LABELS).sort()).toEqual([...stepTypes].sort())
    expect(Object.keys(STEP_TYPE_COLORS).sort()).toEqual([...stepTypes].sort())
    expect(STEP_TYPE_LABELS).toEqual({
      thought: 'thought',
      action: 'action',
      observation: 'observation',
      final: 'final',
      error: 'error',
    })
  })

  it('sorts persisted Task detail steps by timeline order', async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          id: 'task-1',
          title: 'Plan',
          description: 'Plan the work',
          status: 'executing',
          created_at: '2026-06-26T01:00:00Z',
          updated_at: '2026-06-26T01:01:00Z',
          steps: [
            {
              id: 'step-3',
              task_id: 'task-1',
              step_number: 3,
              step_type: 'final',
              content: 'Finished',
            },
            {
              id: 'step-1',
              task_id: 'task-1',
              step_number: 1,
              step_type: 'thought',
              content: 'Plan first',
            },
            {
              id: 'step-2',
              task_id: 'task-1',
              step_number: 2,
              step_type: 'action',
              content: 'Act second',
            },
          ],
        },
      },
    })

    await useTaskStore.getState().fetchTaskDetail('task-1')

    expect(useTaskStore.getState().steps.map((step) => step.id)).toEqual([
      'step-1',
      'step-2',
      'step-3',
    ])
  })

  it('does not fabricate timeline steps when Task detail has no persisted steps', async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          id: 'task-2',
          title: 'Build',
          description: 'Build the work',
          status: 'executing',
          created_at: '2026-06-26T01:00:00Z',
          updated_at: '2026-06-26T01:01:00Z',
        },
      },
    })

    await useTaskStore.getState().fetchTaskDetail('task-2')

    expect(useTaskStore.getState().steps).toEqual([])
  })

  it('keeps SSE step updates sorted when an existing Step order changes', () => {
    mocks.createSSEConnection.mockReturnValue({ close: vi.fn() })
    useTaskStore.setState({
      steps: [
        {
          id: 'step-1',
          taskId: 'task-1',
          order: 1,
          action: 'Started',
          stepType: 'thought',
          status: 'completed',
        },
        {
          id: 'step-2',
          taskId: 'task-1',
          order: 2,
          action: 'Acted',
          stepType: 'action',
          status: 'completed',
        },
      ],
    })

    useTaskStore.getState().subscribeToTask('task-1')
    const config = mocks.createSSEConnection.mock.calls[0][1]

    config.onMessage({
      type: 'step_update',
      step: {
        id: 'step-1',
        task_id: 'task-1',
        step_number: 3,
        step_type: 'observation',
        content: 'Observed later',
      },
    })

    expect(useTaskStore.getState().steps.map((step) => step.id)).toEqual([
      'step-2',
      'step-1',
    ])
  })

  it('tracks Task stream connection status', () => {
    const close = vi.fn()
    mocks.createSSEConnection.mockReturnValue({ close })

    const unsubscribe = useTaskStore.getState().subscribeToTask('task-1')
    const config = mocks.createSSEConnection.mock.calls[0][1]

    expect(useTaskStore.getState().streamStatus).toBe('connecting')

    config.onOpen()
    expect(useTaskStore.getState().streamStatus).toBe('connected')

    config.onError(new Event('error'))
    expect(useTaskStore.getState().streamStatus).toBe('disconnected')

    config.onOpen()
    unsubscribe()

    expect(close).toHaveBeenCalled()
    expect(useTaskStore.getState().streamStatus).toBe('disconnected')
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
