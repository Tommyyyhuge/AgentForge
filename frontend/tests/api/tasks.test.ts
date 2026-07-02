import { describe, expect, it } from 'vitest'
import { toTask, toTaskStep, unwrapApiData } from '../../src/api/tasks'

describe('task API mapping', () => {
  it('unwraps standard success envelopes and legacy raw payloads', () => {
    const wrapped = {
      success: true,
      data: [{ id: 'task-1', title: 'Plan' }],
    } as const
    const raw = [{ id: 'task-2', title: 'Build' }]

    expect(unwrapApiData(wrapped)).toEqual(wrapped.data)
    expect(unwrapApiData(raw)).toEqual(raw)
  })

  it('maps backend task fields into the frontend domain shape', () => {
    expect(
      toTask({
        id: 'task-1',
        title: 'Plan',
        description: 'Plan the work',
        status: 'running',
        assigned_agents: ['agent-coder'],
        dependencies: ['task-0'],
        output: 'Done',
        error_message: '',
        priority: 'high',
        parent_id: 'parent-1',
        created_at: '2026-06-26T01:00:00Z',
        updated_at: '2026-06-26T01:01:00Z',
        completed_at: '2026-06-26T01:02:00Z',
      }),
    ).toEqual({
      id: 'task-1',
      title: 'Plan',
      description: 'Plan the work',
      status: 'executing',
      priority: 'high',
      assignedAgents: ['agent-coder'],
      parentId: 'parent-1',
      dependencies: ['task-0'],
      result: 'Done',
      error: undefined,
      createdAt: '2026-06-26T01:00:00Z',
      updatedAt: '2026-06-26T01:01:00Z',
      completedAt: '2026-06-26T01:02:00Z',
    })
  })

  it('maps backend step fields into the frontend timeline shape', () => {
    expect(
      toTaskStep({
        id: 'step-1',
        task_id: 'task-1',
        agent_id: 'agent-reviewer',
        step_number: 3,
        step_type: 'error',
        content: 'Provider failed',
        tool_output: '401',
        timestamp: '2026-06-26T01:03:00Z',
      }),
    ).toEqual({
      id: 'step-1',
      taskId: 'task-1',
      order: 3,
      action: 'Provider failed',
      stepType: 'error',
      status: 'failed',
      result: '401',
      agentId: 'agent-reviewer',
      startedAt: '2026-06-26T01:03:00Z',
      completedAt: undefined,
    })
  })
})
