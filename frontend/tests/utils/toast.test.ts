import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setToastCallback, toast } from '../../src/utils/toast'

describe('toast', () => {
  let callback: any

  beforeEach(() => {
    callback = vi.fn()
    setToastCallback(callback)
    vi.clearAllMocks()
  })

  it('success 调用回调', () => {
    toast.success('操作成功')
    expect(callback).toHaveBeenCalledWith({
      type: 'success',
      message: '操作成功',
    })
  })

  it('error 调用回调', () => {
    toast.error('操作失败')
    expect(callback).toHaveBeenCalledWith({
      type: 'error',
      message: '操作失败',
    })
  })

  it('info 调用回调', () => {
    toast.info('消息')
    expect(callback).toHaveBeenCalledWith({
      type: 'info',
      message: '消息',
    })
  })

  it('传入 duration', () => {
    toast.success('成功', 5000)
    expect(callback).toHaveBeenCalledWith({
      type: 'success',
      message: '成功',
      duration: 5000,
    })
  })

  it('传入对象参数', () => {
    toast({ type: 'warning', message: '警告', duration: 2000 })
    expect(callback).toHaveBeenCalledWith({
      type: 'warning',
      message: '警告',
      duration: 2000,
    })
  })
})
