import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Send,
  Bot,
  User,
  Loader2,
  Brain,
  Zap,
  Eye,
  Plus,
  MessageSquare,
  Trash2,
} from 'lucide-react'
// Chat 页面纯前端演示，不直接使用后端类型

// ============================================================
// 本地类型
// ============================================================

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** Agent 思考步骤（由 assistant 角色使用） */
  steps?: ThinkStep[]
  timestamp: string
}

interface ThinkStep {
  type: 'thought' | 'action' | 'observation'
  content: string
}

interface Conversation {
  id: string
  title: string
  lastMessage: string
  timestamp: string
}

// ============================================================
// 步骤图标 / 颜色映射
// ============================================================

const STEP_CONFIG = {
  thought:     { icon: <Brain className="h-3.5 w-3.5" />,  label: '思考', color: 'border-forge-400/30 bg-forge-500/10 text-forge-300' },
  action:      { icon: <Zap className="h-3.5 w-3.5" />,     label: '行动', color: 'border-amber-500/30 bg-amber-500/10 text-amber-400' },
  observation: { icon: <Eye className="h-3.5 w-3.5" />,     label: '观察', color: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-400' },
} as const

// ============================================================
// Mock 对话数据
// ============================================================

const MOCK_CONVERSATIONS: Conversation[] = [
  { id: 'conv-1', title: '需求分析 - 用户认证模块', lastMessage: '好的，我已经完成分析...', timestamp: '2 分钟前' },
  { id: 'conv-2', title: '代码审查 - PR #42', lastMessage: '发现3个潜在问题...', timestamp: '1 小时前' },
  { id: 'conv-3', title: '性能优化建议', lastMessage: '建议使用懒加载...', timestamp: '昨天' },
]

const MOCK_MESSAGES: Record<string, ChatMessage[]> = {
  'conv-1': [
    {
      id: 'msg-1', role: 'user',
      content: '请分析以下用户认证模块的需求文档，并给出技术方案。',
      timestamp: '2026-05-21T10:00:00Z',
    },
    {
      id: 'msg-2', role: 'assistant',
      content: '好的，我来分析用户认证模块的需求。以下是技术方案：\n\n1. **认证方式**: JWT + Refresh Token 双令牌机制\n2. **密码加密**: bcrypt + salt\n3. **会话管理**: Redis 缓存 Token 黑名单\n4. **OAuth**: 预留 Google/GitHub 第三方登录接口\n\n推荐技术栈：Passport.js + jsonwebtoken + bcryptjs',
      steps: [
        { type: 'thought', content: '需要先理解认证模块的核心需求：登录、注册、Token管理、权限控制' },
        { type: 'action', content: '查阅 Passport.js 和 JWT 的最佳实践文档' },
        { type: 'thought', content: '双令牌机制可以在安全性和用户体验间取得平衡' },
        { type: 'observation', content: 'JWT access token 有效期建议 15 分钟，refresh token 建议 7 天' },
        { type: 'action', content: '整理技术方案和推荐技术栈' },
      ],
      timestamp: '2026-05-21T10:00:05Z',
    },
    {
      id: 'msg-3', role: 'user',
      content: '如果用户量达到百万级，这套方案有什么需要调整的地方？',
      timestamp: '2026-05-21T10:01:00Z',
    },
    {
      id: 'msg-4', role: 'assistant',
      content: '百万级用户量需要考虑以下调整：\n\n1. **无状态 JWT**: 去掉 Redis 黑名单，改用短期 Token + 签名密钥轮换\n2. **数据库索引**: users 表添加 email/username 的唯一索引\n3. **缓存层**: 高频访问的用户信息放入 Redis 缓存\n4. **限流**: 登录接口添加 rate limiting，防止暴力破解\n5. **水平扩展**: 认证服务无状态化，方便 K8s 自动扩缩容',
      steps: [
        { type: 'thought', content: '百万级用户的核心瓶颈在数据库查询和Token验证' },
        { type: 'action', content: '分析无状态 JWT 方案的优缺点' },
        { type: 'observation', content: '去掉 Redis 黑名单可以消除单点故障，但需要接受短期 Token 泄露风险' },
        { type: 'action', content: '生成调整后的架构方案' },
      ],
      timestamp: '2026-05-21T10:01:10Z',
    },
  ],
}

// ============================================================
// 页面组件
// ============================================================

export default function Chat() {
  const [conversations] = useState<Conversation[]>(MOCK_CONVERSATIONS)
  const [activeConv, setActiveConv] = useState<string>('conv-1')
  const [messages, setMessages] = useState<ChatMessage[]>(MOCK_MESSAGES['conv-1'] ?? [])
  const [input, setInput] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [mobileShowList, setMobileShowList] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 选中对话后切换消息列表
  const handleSelectConv = useCallback((id: string) => {
    setActiveConv(id)
    setMessages(MOCK_MESSAGES[id] ?? [])
    setMobileShowList(false)
  }, [])

  // 新对话
  const handleNewChat = useCallback(() => {
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: '新对话',
      lastMessage: '',
      timestamp: '刚刚',
    }
    // 此处仅 UI 演示，不持久化
    setActiveConv(newConv.id)
    setMessages([])
    setMobileShowList(false)
  }, [])

  // 发送消息
  const handleSend = useCallback(() => {
    const trimmed = input.trim()
    if (!trimmed || isSending) return

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsSending(true)

    // 模拟 Agent 响应
    setTimeout(() => {
      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now() + 1}`,
        role: 'assistant',
        content: `收到你的消息：「${trimmed}」\n\n这是一个演示回复。实际环境中将由 Agent 处理你的任务请求并返回执行结果。`,
        steps: [
          { type: 'thought', content: `理解用户意图：${trimmed.slice(0, 50)}${trimmed.length > 50 ? '...' : ''}` },
          { type: 'action', content: '分析任务复杂度并拆解为子任务' },
          { type: 'observation', content: '任务已加入执行队列，等待 Agent 处理' },
        ],
        timestamp: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setIsSending(false)
    }, 2000)
  }, [input, isSending])

  // 键盘发送
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }, [handleSend])

  // 自动滚到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-6xl gap-0 overflow-hidden rounded-forge border border-surface-border animate-slide-up">
      <aside
        className={`
          flex w-60 shrink-0 flex-col border-r border-surface-border bg-surface-dark
          ${mobileShowList ? 'flex' : 'hidden'}
          sm:flex
        `}
      >
        {/* 顶部：新对话按钮 */}
        <div className="border-b border-surface-border p-3">
          <button
            onClick={handleNewChat}
            className="forge-btn-primary flex w-full items-center justify-center gap-2 !py-2 text-sm"
          >
            <Plus className="h-4 w-4" />
            新对话
          </button>
        </div>

        {/* 对话列表 */}
        <div className="flex-1 overflow-y-auto">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => handleSelectConv(conv.id)}
              className={`
                w-full px-3 py-3 text-left transition-colors
                ${activeConv === conv.id
                  ? 'bg-forge-500/10 border-l-2 border-forge-400'
                  : 'border-l-2 border-transparent hover:bg-white/[0.03]'
                }
              `}
            >
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 shrink-0 text-neutral-500" />
                <div className="min-w-0 flex-1">
                  <p className={`text-sm font-medium text-truncate ${activeConv === conv.id ? 'text-white' : 'text-neutral-300'}`}>
                    {conv.title}
                  </p>
                  <p className="mt-0.5 text-xs text-neutral-500 text-truncate">{conv.lastMessage}</p>
                </div>
              </div>
              <p className="mt-1 text-[10px] text-neutral-600">{conv.timestamp}</p>
            </button>
          ))}
        </div>

        {/* 底部：删除对话 */}
        <div className="border-t border-surface-border p-2">
          <button className="forge-btn-ghost flex w-full items-center gap-2 text-xs text-neutral-500 hover:text-red-400">
            <Trash2 className="h-3.5 w-3.5" />
            清空对话
          </button>
        </div>
      </aside>
      <div className="flex flex-1 flex-col bg-surface-dark">
        {/* 移动端返回按钮 */}
        {!mobileShowList && (
          <div className="flex items-center gap-2 border-b border-surface-border px-4 py-2 sm:hidden">
            <button
              onClick={() => setMobileShowList(true)}
              className="text-sm text-forge-400"
            >
              ← 对话列表
            </button>
          </div>
        )}

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center space-y-2">
                <Bot className="mx-auto h-12 w-12 text-neutral-600" />
                <p className="text-neutral-500">开始一段新对话</p>
                <p className="text-xs text-neutral-600">输入任务描述，Agent 将协助你完成</p>
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                {/* 头像 */}
                {msg.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-forge-500/10 ring-1 ring-forge-500/20">
                    <Bot className="h-4 w-4 text-forge-400" />
                  </div>
                )}

                <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                  {/* 消息气泡 */}
                  <div
                    className={`
                      rounded-forge px-4 py-3 text-sm leading-relaxed
                      ${msg.role === 'user'
                        ? 'bg-forge-500/20 text-neutral-200 ml-auto'
                        : 'bg-white/[0.04] text-neutral-300'
                      }
                    `}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {/* Agent 思考步骤 */}
                  {msg.steps && msg.steps.length > 0 && (
                    <div className="mt-2 space-y-1.5 pl-1">
                      {msg.steps.map((step, idx) => (
                        <div
                          key={`${msg.id}-step-${idx}`}
                          className={`flex items-start gap-2 rounded-md border px-3 py-2 text-xs ${STEP_CONFIG[step.type].color}`}
                        >
                          <span className="mt-0.5 shrink-0">{STEP_CONFIG[step.type].icon}</span>
                          <div className="min-w-0">
                            <span className="font-medium">{STEP_CONFIG[step.type].label}</span>
                            <span className="mx-1 text-neutral-500">·</span>
                            <span className="text-neutral-400">{step.content}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* 时间戳 */}
                  <p className={`mt-1 text-[10px] text-neutral-600 ${msg.role === 'user' ? 'text-right' : ''}`}>
                    {new Date(msg.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>

                {/* 用户头像 */}
                {msg.role === 'user' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent/20 ring-1 ring-accent/30">
                    <User className="h-4 w-4 text-accent-light" />
                  </div>
                )}
              </div>
            ))
          )}

          {/* 发送中动画 */}
          {isSending && (
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-forge-500/10 ring-1 ring-forge-500/20">
                <Loader2 className="h-4 w-4 animate-spin text-forge-400" />
              </div>
              <div className="flex items-center gap-1.5 rounded-forge bg-white/[0.04] px-4 py-3">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400" style={{ animationDelay: '0ms' }} />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400" style={{ animationDelay: '150ms' }} />
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-neutral-400" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="border-t border-surface-border p-3">
          <div className="flex items-end gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入任务描述..."
              rows={1}
              className="flex-1 resize-none rounded-forge border border-surface-border
                         bg-white/[0.03] px-3 py-2.5 text-sm text-white
                         placeholder:text-neutral-600
                         outline-none transition-colors
                         focus:border-forge-500/40 focus:ring-1 focus:ring-forge-500/20"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isSending}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-forge
                         bg-forge-500 text-white transition-all duration-200
                         hover:bg-forge-700 active:scale-[0.98]
                         disabled:cursor-not-allowed disabled:opacity-40"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
