import { describe, expect, it } from 'vitest'
import { toAgent, unwrapApiData } from '../../src/api/agents'

describe('agent API mapping', () => {
  it('unwraps standard success envelopes and legacy raw payloads', () => {
    const wrapped = {
      success: true,
      data: [{ id: 'agent-researcher', role: 'researcher' }],
    } as const
    const raw = [{ id: 'agent-coder', role: 'coder' }]

    expect(unwrapApiData(wrapped)).toEqual(wrapped.data)
    expect(unwrapApiData(raw)).toEqual(raw)
  })

  it('maps backend agent fields into the frontend domain shape', () => {
    expect(
      toAgent({
        id: 'agent-reviewer',
        role: 'reviewer',
        name: 'Reviewer',
        status: 'thinking',
        description: 'Checks work',
        model: 'deepseek-chat',
        current_task_id: 'task-1',
        created_at: '2026-06-26T01:00:00Z',
        updated_at: '2026-06-26T01:01:00Z',
      }),
    ).toEqual({
      id: 'agent-reviewer',
      name: 'Reviewer',
      role: 'reviewer',
      status: 'busy',
      description: 'Checks work',
      model: 'deepseek-chat',
      createdAt: '2026-06-26T01:00:00Z',
      updatedAt: '2026-06-26T01:01:00Z',
    })
  })

  it('does not expose planner as an executable frontend agent role', () => {
    expect(
      toAgent({
        id: 'agent-planner',
        role: 'planner',
        status: 'idle',
      }),
    ).toMatchObject({
      id: 'agent-planner',
      role: 'executor',
      status: 'idle',
    })
  })
})
