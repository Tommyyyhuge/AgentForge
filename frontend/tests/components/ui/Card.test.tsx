import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Card from '../../../src/components/ui/Card'

describe('Card', () => {
  it('渲染 children', () => {
    render(<Card>卡片内容</Card>)
    expect(screen.getByText('卡片内容')).toBeInTheDocument()
  })

  it('className 合并', () => {
    render(<Card className="custom">内容</Card>)
    expect(screen.getByText('内容').className).toContain('custom')
  })

  it('点击触发 onClick', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    const onClick = vi.fn()
    render(<Card onClick={onClick}>可点击</Card>)
    await userEvent.click(screen.getByText('可点击'))
    expect(onClick).toHaveBeenCalledOnce()
  })
})
