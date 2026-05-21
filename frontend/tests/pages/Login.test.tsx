import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import Login from '../../src/pages/Login'

// Mock auth store
const mockLogin = vi.fn()
const mockClearError = vi.fn()

vi.mock('../../src/stores/authStore', () => ({
  useAuthStore: () => ({
    login: mockLogin,
    isLoading: false,
    error: null,
    clearError: mockClearError,
  }),
}))

describe('Login', () => {
  beforeEach(() => {
    mockLogin.mockReset()
    mockClearError.mockReset()
  })

  it('渲染登录表单', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    expect(screen.getByText('欢迎回来')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /登录/i })).toBeInTheDocument()
  })

  it('空用户名显示校验错误', async () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    const submitBtn = screen.getByRole('button', { name: /登录/i })
    await userEvent.click(submitBtn)
    await waitFor(() => {
      expect(screen.getByText(/请输入用户名/)).toBeInTheDocument()
    })
  })

  it('提交表单调用 login', async () => {
    mockLogin.mockResolvedValue(undefined)
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )

    await userEvent.type(screen.getByPlaceholderText(/用户名/), 'admin')
    await userEvent.type(screen.getByPlaceholderText(/密码/), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /登录/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin', 'password123')
    })
  })

  it('有注册链接', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    expect(screen.getByText('立即注册').closest('a')).toHaveAttribute('href', '/register')
  })
})
