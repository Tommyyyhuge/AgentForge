import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Dashboard from '../../src/pages/Dashboard'

const storeMocks = vi.hoisted(() => ({
  metrics: {
    fetchDashboardMetrics: vi.fn(),
  },
  taskState: {
    tasks: [] as unknown[],
    isLoading: false,
    fetchTasks: vi.fn(),
  },
  agentState: {
    agents: [] as unknown[],
    isLoading: false,
    fetchAgents: vi.fn(),
    subscribeToAgents: vi.fn(() => vi.fn()),
  },
  providerState: {
    providers: [] as unknown[],
    healthByProviderId: {} as Record<string, unknown>,
    isLoading: false,
    error: null as string | null,
    fetchProviderSettings: vi.fn(),
  },
}))

vi.mock('../../src/api/metrics', () => ({
  fetchDashboardMetrics: storeMocks.metrics.fetchDashboardMetrics,
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
}))

vi.mock('../../src/stores/agentStore', () => ({
  useAgentStore: () => storeMocks.agentState,
  AGENT_STATUS_COLORS: {
    idle: 'idle',
    busy: 'busy',
    error: 'error',
  },
  AGENT_STATUS_LABELS: {
    idle: 'idle',
    busy: 'busy',
    error: 'error',
  },
}))

vi.mock('../../src/stores/providerStore', () => ({
  useProviderStore: () => storeMocks.providerState,
}))

function renderDashboard() {
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  )
}

describe('Dashboard Provider status', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    storeMocks.taskState.tasks = []
    storeMocks.taskState.isLoading = false
    storeMocks.agentState.agents = []
    storeMocks.agentState.isLoading = false
    storeMocks.providerState.providers = []
    storeMocks.providerState.healthByProviderId = {}
    storeMocks.providerState.isLoading = false
    storeMocks.providerState.error = null
    storeMocks.metrics.fetchDashboardMetrics.mockResolvedValue({
      taskMetrics: [],
      agentMetrics: [],
      systemMetrics: {
        cpuUsage: 0,
        memoryUsage: 0,
        activeTasks: 0,
        totalRequests: 0,
      },
    })
  })

  it('warns when no active Provider is configured', () => {
    renderDashboard()

    expect(storeMocks.providerState.fetchProviderSettings).toHaveBeenCalled()
    expect(screen.getByText('Provider attention required')).toBeInTheDocument()
    expect(screen.getByText('No active Provider is configured.')).toBeInTheDocument()
  })

  it('warns when all active Providers are unhealthy', () => {
    storeMocks.providerState.providers = [
      {
        id: 'provider-openai',
        providerType: 'openai',
        displayName: 'OpenAI',
        isActive: true,
      },
    ]
    storeMocks.providerState.healthByProviderId = {
      'provider-openai': {
        status: 'unhealthy',
        errorMessage: 'Provider authentication failed.',
      },
    }

    renderDashboard()

    expect(screen.getByText('Provider attention required')).toBeInTheDocument()
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('unhealthy')).toBeInTheDocument()
  })

  it('shows Provider ready summary when an active Provider is healthy', () => {
    storeMocks.providerState.providers = [
      {
        id: 'provider-openai',
        providerType: 'openai',
        displayName: 'OpenAI',
        defaultModel: 'gpt-4o-mini',
        isActive: true,
      },
    ]
    storeMocks.providerState.healthByProviderId = {
      'provider-openai': {
        status: 'healthy',
      },
    }

    renderDashboard()

    expect(screen.getByText('Providers ready')).toBeInTheDocument()
    expect(screen.getByText('1 active Provider')).toBeInTheDocument()
    expect(screen.getByText('gpt-4o-mini')).toBeInTheDocument()
  })

  it('shows metrics error state without hiding primary navigation', async () => {
    storeMocks.metrics.fetchDashboardMetrics.mockRejectedValueOnce(new Error('metrics unavailable'))

    renderDashboard()

    expect(await screen.findByText('Metrics unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '创建任务' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Provider Settings' })).toBeInTheDocument()
  })

  it('shows an Agent status summary before the recent Agent list', () => {
    storeMocks.agentState.agents = [
      {
        id: 'agent-researcher',
        name: 'Researcher',
        description: 'Research tasks',
        status: 'busy',
      },
      {
        id: 'agent-coder',
        name: 'Coder',
        description: 'Code tasks',
        status: 'idle',
      },
      {
        id: 'agent-reviewer',
        name: 'Reviewer',
        description: 'Review tasks',
        status: 'error',
      },
    ]

    renderDashboard()

    expect(screen.getByText('Agent summary')).toBeInTheDocument()
    expect(screen.getByText('1 busy')).toBeInTheDocument()
    expect(screen.getByText('1 idle')).toBeInTheDocument()
    expect(screen.getByText('1 error')).toBeInTheDocument()
  })
})
