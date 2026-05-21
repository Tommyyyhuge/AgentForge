import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Button from '../../../src/components/ui/Button'

describe('Button', () => {
  it('渲染按钮文本', () => {
    render(<Button>点击我</Button>)
    expect(screen.getByRole('button', { name: /点击我/i })).toBeInTheDocument()
  })

  it('点击触发 onClick', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>点击</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('disabled 时不触发点击', async () => {
    const onClick = vi.fn()
    render(<Button disabled onClick={onClick}>点击</Button>)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).not.toHaveBeenCalled()
  })

  it('loading 时显示 spinner 且禁用', () => {
    const { container } = render(<Button isLoading>提交</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    // 检查 Loading spinner 是否渲染（Loading 组件会在内部渲染 SVG）
    expect(container.querySelector('[class*="animate-spin"]')).toBeTruthy()
  })

  it('variant=primary 有 forge 背景色', () => {
    render(<Button variant="primary">primary</Button>)
    expect(screen.getByRole('button').className).toContain('bg-forge-500')
  })

  it('variant=danger 有红色样式', () => {
    render(<Button variant="danger">删除</Button>)
    expect(screen.getByRole('button').className).toContain('bg-red-500')
  })

  it('size=sm 渲染小尺寸', () => {
    render(<Button size="sm">小按钮</Button>)
    expect(screen.getByRole('button').className).toContain('text-xs')
  })
})
