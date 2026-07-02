import { beforeEach, describe, expect, it, vi } from 'vitest'

class FakeEventSource {
  static instances: FakeEventSource[] = []

  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  readyState = 0
  listeners: Record<string, (event: MessageEvent) => void> = {}
  url: string

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners[type] = listener
  }

  close() {
    this.readyState = 2
  }
}

describe('createSSEConnection', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    vi.resetModules()
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  it('routes named backend SSE events through onMessage', async () => {
    const { createSSEConnection } = await import('../../src/api/client')
    const onMessage = vi.fn()

    createSSEConnection('/tasks/task-1/stream', { onMessage })
    const source = FakeEventSource.instances[0]

    source.listeners.step({ data: '{"type":"step_update"}' } as MessageEvent)
    source.listeners.done({ data: '{"type":"done"}' } as MessageEvent)
    source.listeners.agent_state({ data: '{"type":"agent_update"}' } as MessageEvent)

    expect(onMessage).toHaveBeenNthCalledWith(1, { type: 'step_update' }, 'step')
    expect(onMessage).toHaveBeenNthCalledWith(2, { type: 'done' }, 'done')
    expect(onMessage).toHaveBeenNthCalledWith(3, { type: 'agent_update' }, 'agent_state')
  })
})
