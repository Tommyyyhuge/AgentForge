import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAgentStore } from '../../src/stores/agentStore'

const mocks = vi.hoisted(() => ({
  get: vi.fn(),
  createSSEConnection: vi.fn(),
}))

vi.mock('../../src/api/client', () => ({
  default: {
    get: mocks.get,
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  createSSEConnection: mocks.createSSEConnection,
}))

describe('agentStore API contract', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAgentStore.setState({
      agents: [],
      isLoading: false,
      error: null,
    })
  })

  it('normalizes wrapped backend agents into the UI agent shape', async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        success: true,
        data: [
          {
            id: 'agent-researcher',
            role: 'researcher',
            name: 'Researcher',
            status: 'idle',
            current_task_id: null,
            created_at: '2026-06-26T01:00:00Z',
          },
        ],
      },
    })

    await useAgentStore.getState().fetchAgents()

    expect(useAgentStore.getState().agents[0]).toMatchObject({
      id: 'agent-researcher',
      role: 'researcher',
      status: 'idle',
      model: 'configured-llm',
      createdAt: '2026-06-26T01:00:00Z',
      updatedAt: '2026-06-26T01:00:00Z',
    })
  })

  it('normalizes agent SSE update events', () => {
    mocks.createSSEConnection.mockReturnValue({ close: vi.fn() })

    useAgentStore.getState().subscribeToAgents()
    const config = mocks.createSSEConnection.mock.calls[0][1]
    config.onMessage({
      type: 'agent_update',
      agent: {
        id: 'agent-coder',
        role: 'coder',
        name: 'Coder',
        status: 'idle',
        current_task_id: null,
        created_at: '2026-06-26T01:00:00Z',
      },
    })

    expect(useAgentStore.getState().agents[0]).toMatchObject({
      id: 'agent-coder',
      role: 'coder',
      status: 'idle',
      createdAt: '2026-06-26T01:00:00Z',
    })
  })
})
