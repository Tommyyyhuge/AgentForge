import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import Chat from '../../src/pages/Chat'

const taskMocks = vi.hoisted(() => ({
  createTask: vi.fn(),
}))

vi.mock('../../src/stores/taskStore', () => ({
  useTaskStore: () => ({
    createTask: taskMocks.createTask,
  }),
}))

function renderChat() {
  render(
    <MemoryRouter initialEntries={['/chat']}>
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/tasks/:id" element={<div>Task detail route</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Chat Task intake', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Element.prototype.scrollIntoView = vi.fn()
    taskMocks.createTask.mockResolvedValue({
      id: 'task-created',
      title: 'Investigate provider errors',
      description: 'Investigate provider errors',
      status: 'pending',
      priority: 'medium',
      assignedAgents: [],
      dependencies: [],
      createdAt: '2026-07-02T01:00:00Z',
      updatedAt: '2026-07-02T01:00:00Z',
    })
  })

  it('renders an empty Task intake state instead of mock conversations', () => {
    renderChat()

    expect(screen.queryByText('需求分析 - 用户认证模块')).not.toBeInTheDocument()
    expect(screen.queryByText(/演示回复/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('Task 描述')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create Task from Chat' })).toBeInTheDocument()
  })

  it('creates a real Task from the submitted prompt and navigates to Task detail', async () => {
    renderChat()

    await userEvent.type(screen.getByLabelText('Task 描述'), 'Investigate provider errors')
    await userEvent.click(screen.getByRole('button', { name: 'Create Task from Chat' }))

    expect(taskMocks.createTask).toHaveBeenCalledWith({
      title: 'Investigate provider errors',
      description: 'Investigate provider errors',
    })
    expect(await screen.findByText('Task detail route')).toBeInTheDocument()
  })
})
