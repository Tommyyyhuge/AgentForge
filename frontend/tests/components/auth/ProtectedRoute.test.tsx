import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProtectedRoute from '../../../src/components/auth/ProtectedRoute'

// Mock auth store
const mockIsAuth = vi.fn(() => false)
const mockIsLoading = vi.fn(() => false)

vi.mock('../../../src/stores/authStore', () => ({
  useAuthStore: () => ({
    isAuthenticated: mockIsAuth(),
    isLoading: mockIsLoading(),
  }),
}))

describe('ProtectedRoute', () => {
  beforeEach(() => {
    mockIsAuth.mockReturnValue(false)
    mockIsLoading.mockReturnValue(false)
  })

  function renderRoute() {
    return render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<span>Login Page</span>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <span>Dashboard</span>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )
  }

  it('未登录重定向到登录页', () => {
    renderRoute()
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('已登录渲染子组件', () => {
    mockIsAuth.mockReturnValue(true)
    renderRoute()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})

