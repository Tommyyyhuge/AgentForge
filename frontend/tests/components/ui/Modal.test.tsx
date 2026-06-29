import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Modal from '../../../src/components/ui/Modal'

describe('Modal', () => {
  const onClose = vi.fn()

  beforeEach(() => {
    onClose.mockReset()
  })

  it('isOpen=true 渲染内容', () => {
    render(
      <Modal isOpen={true} onClose={onClose} title="测试">
        <p>模态框内容</p>
      </Modal>
    )
    expect(screen.getByText('测试')).toBeInTheDocument()
    expect(screen.getByText('模态框内容')).toBeInTheDocument()
  })

  it('isOpen=false 不渲染', () => {
    render(
      <Modal isOpen={false} onClose={onClose}>
        <p>不应看到</p>
      </Modal>
    )
    expect(screen.queryByText('不应看到')).not.toBeInTheDocument()
  })

  it('点击关闭按钮触发 onClose', async () => {
    render(
      <Modal isOpen={true} onClose={onClose} title="测试">
        <p>内容</p>
      </Modal>
    )
    await userEvent.click(screen.getByLabelText('关闭'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('ESC 键触发 onClose', async () => {
    render(
      <Modal isOpen={true} onClose={onClose}>
        <p>内容</p>
      </Modal>
    )
    await userEvent.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('open 时锁定背景滚动', () => {
    render(
      <Modal isOpen={true} onClose={onClose}>
        <p>内容</p>
      </Modal>
    )
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('渲染 footer', () => {
    render(
      <Modal isOpen={true} onClose={onClose} footer={<button>确定</button>}>
        <p>内容</p>
      </Modal>
    )
    expect(screen.getByText('确定')).toBeInTheDocument()
  })
})
