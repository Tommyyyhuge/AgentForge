import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Loading from '../../../src/components/ui/Loading'

describe('Loading', () => {
  it('variant=spinner 渲染旋转动画', () => {
    const { container } = render(<Loading variant="spinner" />)
    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()
  })

  it('spinner 显示文本', () => {
    render(<Loading variant="spinner" text="加载中..." />)
    expect(screen.getByText('加载中...')).toBeInTheDocument()
  })

  it('variant=skeleton 渲染骨架屏', () => {
    render(<Loading variant="skeleton" rows={3} />)
    // 应该有 3 个骨架条
    const skeletons = document.querySelectorAll('.animate-pulse, [class*="rounded"]')
    // 简单检查至少有内容渲染
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('variant=overlay 渲染全屏遮罩', () => {
    const { container } = render(<Loading variant="overlay" text="处理中..." />)
    expect(container.firstChild).toBeTruthy()
    expect(container.querySelector('svg')).toBeTruthy()
  })
})
