# Week 4 实施计划

> **基于设计文档**: `docs/superpowers/specs/2026-05-21-week4-design.md`  
> **开发周期**: 7 天（Day 0 - Day 6）  
> **核心原则**: 测试驱动、增量交付

---

## 目录

1. [依赖安装 (Day 0)](#1-依赖安装-day-0)
2. [基础 UI 组件 (Day 1)](#2-基础-ui-组件-day-1)
3. [主题系统 (Day 2)](#3-主题系统-day-2)
4. [登录/注册 + 路由守卫 (Day 3)](#4-登录注册--路由守卫-day-3)
5. [Agent 协作流程图 (Day 4-5)](#5-agent-协作流程图-day-4-5)
6. [性能监控图表 (Day 6)](#6-性能监控图表-day-6)
7. [联调 + 测试 (Day 7)](#7-联调--测试-day-7)
8. [文件清单汇总](#8-文件清单汇总)
9. [风险缓解](#9-风险缓解)

---

## 1. 依赖安装 (Day 0)

### 1.1 安装前端依赖

**命令**:
```bash
cd frontend
npm install reactflow recharts framer-motion
```

**依赖说明**:
| 包 | 版本 | 用途 |
|----|------|------|
| reactflow | ^11.x | Agent 协作流程图 |
| recharts | ^2.x | 性能监控图表 |
| framer-motion | ^11.x | 动画效果 |

### 1.2 验证安装

**检查**:
- [ ] `package.json` 包含新依赖
- [ ] `node_modules` 已安装
- [ ] `npm run build` 成功
- [ ] `npm run lint` 无错误

---

## 2. 基础 UI 组件 (Day 1)

### 2.1 上午: Modal + Loading

#### Task 2.1.1: Modal 组件

**文件**: `frontend/src/components/ui/Modal.tsx`

**实现要点**:
- 使用 `framer-motion` 实现进入/退出动画（fade + scale）
- 支持 ESC 键关闭
- 点击遮罩层关闭（可配置）
- 打开时锁定背景滚动
- 自动聚焦第一个可交互元素
- 支持 4 种尺寸（sm/md/lg/xl）

**Props**:
```typescript
interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  description?: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl'
  closeOnOverlay?: boolean  // 默认 true
}
```

**测试要点**:
- [ ] 打开/关闭动画流畅
- [ ] ESC 键关闭有效
- [ ] 点击遮罩关闭有效
- [ ] 背景滚动锁定
- [ ] 焦点管理正确

**依赖**: framer-motion

#### Task 2.1.2: Loading 组件

**文件**: `frontend/src/components/ui/Loading.tsx`

**实现要点**:
- 3 种变体：Spinner、Skeleton、Overlay
- Spinner 支持不同尺寸
- Skeleton 支持行数和宽度自定义
- Overlay 支持全屏/局部覆盖

**Props**:
```typescript
interface LoadingProps {
  variant: 'spinner' | 'skeleton' | 'overlay'
  text?: string
  className?: string
  rows?: number  // skeleton 专用
}
```

**测试要点**:
- [ ] 3 种变体正确渲染
- [ ] Spinner 有旋转动画
- [ ] Skeleton 有脉冲动画
- [ ] Overlay 有半透明背景

**依赖**: 无（纯 Tailwind）

### 2.2 下午: Toast + Button

#### Task 2.2.1: Toast 组件 + ToastContainer

**文件**:
- `frontend/src/components/ui/Toast.tsx`
- `frontend/src/components/ui/ToastContainer.tsx`
- `frontend/src/hooks/useToast.ts`

**实现要点**:
- 使用 `framer-motion` 实现滑入/淡出动画
- 4 种类型：success/error/warning/info
- 自动关闭（默认 3000ms，可配置）
- 支持同时显示多个 Toast（最多 5 个）
- 点击关闭
- 进度条显示剩余时间

**API**:
```typescript
// hooks/useToast.ts
export function useToast() {
  return {
    success: (message: string, duration?: number) => void
    error: (message: string, duration?: number) => void
    warning: (message: string, duration?: number) => void
    info: (message: string, duration?: number) => void
  }
}
```

**使用示例**:
```tsx
const { success, error } = useToast()
success('任务创建成功')
error('操作失败，请重试')
```

**测试要点**:
- [ ] Toast 正确显示
- [ ] 自动关闭有效
- [ ] 多个 Toast 堆叠正确
- [ ] 动画流畅

**依赖**: framer-motion

#### Task 2.2.2: Button 组件

**文件**: `frontend/src/components/ui/Button.tsx`

**实现要点**:
- 4 种变体：primary、secondary、ghost、danger
- 3 种尺寸：sm、md、lg
- 支持 loading 状态（内置 Spinner）
- 支持图标前缀/后缀
- 使用 `framer-motion` 实现点击缩放动画
- 统一禁用/加载样式

**Props**:
```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  leftIcon?: ReactNode
  rightIcon?: ReactNode
}
```

**测试要点**:
- [ ] 4 种变体样式正确
- [ ] loading 状态显示 spinner
- [ ] 禁用状态样式正确
- [ ] 点击动画流畅

**依赖**: framer-motion

### 2.3 Day 1 验证

- [ ] 所有组件可独立渲染
- [ ] 交互行为正确
- [ ] 动画流畅（framer-motion）
- [ ] 暗色主题下样式正确

---

## 3. 主题系统 (Day 2)

### 3.1 上午: CSS 变量 + Hook

#### Task 3.1.1: CSS 变量扩展

**文件**: `frontend/src/index.css`

**修改内容**:
- 扩展 `:root` 亮色主题变量
- 确保 `.dark` 暗色主题变量完整
- 所有颜色使用 CSS 变量

**变量清单**:
```css
:root {
  --surface-bg: #ffffff;
  --surface-light: #f8fafc;
  --surface-border: #e2e8f0;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --forge-500: #1a3fff;
  --forge-700: #091aa3;
}

.dark {
  --surface-bg: #0a0a0a;
  --surface-light: #141414;
  --surface-border: #262626;
  --text-primary: #fafafa;
  --text-secondary: #a3a3a3;
  --text-muted: #525252;
}
```

#### Task 3.1.2: useTheme Hook

**文件**: `frontend/src/hooks/useTheme.ts`

**实现要点**:
- 使用 Zustand + persist 管理主题状态
- 支持 'light' | 'dark' | 'system' 三种模式
- system 模式监听 `prefers-color-scheme`
- 切换时更新 `<html>` 元素的 class
- 避免 FOUC（闪烁）

**状态结构**:
```typescript
type Theme = 'light' | 'dark' | 'system'

interface ThemeStore {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
}
```

**关键逻辑**:
```typescript
// 初始化时应用主题
function applyTheme(theme: 'light' | 'dark') {
  const html = document.documentElement
  if (theme === 'dark') {
    html.classList.add('dark')
  } else {
    html.classList.remove('dark')
  }
}
```

### 3.2 下午: 组件适配 + Settings 集成

#### Task 3.2.1: 现有组件适配

**修改文件**:
- `components/layout/Layout.tsx`
- `components/layout/Header.tsx`
- `components/layout/Sidebar.tsx`
- `pages/Dashboard.tsx`
- `pages/Tasks.tsx`
- `pages/TaskDetail.tsx`
- `pages/AgentMonitor.tsx`
- `pages/Chat.tsx`
- `pages/Settings.tsx`

**适配要点**:
- 背景色使用 `bg-[var(--surface-bg)]` 或 Tailwind 的 `dark:` 前缀
- 文字色使用 `text-[var(--text-primary)]`
- 边框色使用 `border-[var(--surface-border)]`
- 检查所有硬编码颜色值

#### Task 3.2.2: Settings 页面集成主题切换

**修改文件**: `frontend/src/pages/Settings.tsx`

**添加内容**:
- 主题选择器（Radio group 或 Select）
- 实时预览切换效果
- 持久化到 localStorage

### 3.3 Day 2 验证

- [ ] 可在 light/dark/system 间切换
- [ ] 切换无闪烁
- [ ] 偏好持久化
- [ ] 所有页面适配两种主题
- [ ] 构建成功

---

## 4. 登录/注册 + 路由守卫 (Day 3)

### 4.1 上午: 登录 + 注册页面

#### Task 4.1.1: Login 页面

**文件**: `frontend/src/pages/Login.tsx`

**实现要点**:
- 居中卡片式布局
- 左侧品牌信息（大屏显示）
- 右侧表单区域
- 表单字段：用户名、密码
- 密码显示/隐藏切换
- "记住我"选项
- 表单校验（非空、最小长度）
- 登录按钮（loading 状态）
- 错误提示（Toast）
- 暗色/亮色主题自适应

**集成**:
- 调用 `authStore.login()`
- 登录成功后跳转（优先跳转到 `location.state.from`）

#### Task 4.1.2: Register 页面

**文件**: `frontend/src/pages/Register.tsx`

**实现要点**:
- 与 Login 一致的布局风格
- 表单字段：用户名、邮箱、密码、确认密码
- 实时校验：
  - 用户名：3-20 字符，字母数字下划线
  - 邮箱：格式校验
  - 密码：最少 8 位，包含字母和数字
  - 确认密码：一致性校验
- 密码强度提示
- 注册按钮（loading 状态）
- 错误提示（Toast）

**集成**:
- 调用 `authStore.register()`
- 注册成功后自动登录或跳转登录页

### 4.2 下午: 路由守卫 + 路由配置

#### Task 4.2.1: ProtectedRoute 组件

**文件**: `frontend/src/components/auth/ProtectedRoute.tsx`

**实现要点**:
- 检查 `authStore.isAuthenticated`
- 未登录重定向到 `/login`，保留原路径
- 已登录放行
- loading 状态显示 Loading overlay

```typescript
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  const location = useLocation()
  
  if (isLoading) return <Loading variant="overlay" />
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}
```

#### Task 4.2.2: App.tsx 路由配置

**修改文件**: `frontend/src/App.tsx`

**更新内容**:
```tsx
<Routes>
  {/* 公开路由 */}
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  
  {/* 受保护路由 */}
  <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
  <Route path="/tasks" element={<ProtectedRoute><Tasks /></ProtectedRoute>} />
  <Route path="/tasks/:id" element={<ProtectedRoute><TaskDetail /></ProtectedRoute>} />
  <Route path="/agents" element={<ProtectedRoute><AgentMonitor /></ProtectedRoute>} />
  <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
  <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
</Routes>
```

### 4.3 Day 3 验证

- [ ] 可访问 /login 和 /register
- [ ] 表单客户端校验有效
- [ ] 登录成功后跳转正确
- [ ] 未登录访问受保护路由重定向
- [ ] Token 自动附加到 API 请求
- [ ] 暗色/亮色主题下样式正确

---

## 5. Agent 协作流程图 (Day 4-5)

### 5.1 Day 4 上午: React Flow 基础

#### Task 5.1.1: React Flow 配置

**文件**:
- `frontend/src/components/flow/AgentFlow.tsx`
- `frontend/src/components/flow/AgentNode.tsx`
- `frontend/src/types/flow.ts`

**实现要点**:
- 安装并配置 React Flow
- 自定义 Agent 节点组件
- 节点样式与暗色主题一致
- 支持缩放、平移、适配视图

**AgentNode 设计**:
```tsx
function AgentNode({ data }: NodeProps<AgentNodeData>) {
  const statusColor = AGENT_STATUS_COLORS[data.status]
  return (
    <motion.div className={`forge-flow-node ${statusColor}`} layout>
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center gap-2">
        {ROLE_ICONS[data.role]}
        <div>
          <div className="font-medium">{data.name}</div>
          <div className="text-xs text-neutral-400">{data.model}</div>
        </div>
      </div>
      <Badge status={data.status} />
      <Handle type="source" position={Position.Bottom} />
    </motion.div>
  )
}
```

#### Task 5.1.2: DAG 布局算法

**文件**: `frontend/src/components/flow/layout.ts`

**实现要点**:
- 分层布局算法
- 计算节点位置
- 避免边交叉

```typescript
function calculateLayout(nodes: AgentNode[], edges: AgentEdge[]): PositionedNode[]
```

### 5.2 Day 4 下午: 静态流程图

#### Task 5.2.1: 任务流程图数据生成

**后端文件**: `backend/agent_forge/api/routes/tasks.py`（扩展）

**新增端点**:
```
GET /api/v1/tasks/{id}/flow
```

**响应**:
```json
{
  "nodes": [
    {
      "id": "agent-1",
      "type": "agent",
      "data": { "name": "Prometheus", "role": "orchestrator", "status": "executing" },
      "position": { "x": 100, "y": 100 }
    }
  ],
  "edges": [
    { "id": "e-1-2", "source": "agent-1", "target": "agent-2", "animated": false }
  ]
}
```

**实现逻辑**:
- 从任务的 `assignedAgents` 和 `dependencies` 生成节点
- 根据 Agent 角色确定层次
- 返回节点位置（后端计算或前端计算）

#### Task 5.2.2: AgentMonitor 页面集成

**修改文件**: `frontend/src/pages/AgentMonitor.tsx`

**添加内容**:
- 标签页切换：列表视图 / 流程图视图
- 流程图视图使用 AgentFlow 组件

### 5.3 Day 5 上午: 实时状态更新

#### Task 5.3.1: 实时状态同步

**实现要点**:
- 使用现有 SSE 连接 (`agentStore.subscribeToAgents()`)
- 节点颜色随状态实时变化
- 使用 framer-motion `layout` 动画平滑过渡

#### Task 5.3.2: 消息传递动画

**实现要点**:
- 消息传递时边线动画（脉冲效果）
- 使用 React Flow 的 `animated` 属性

### 5.4 Day 5 下午: TaskDetail 集成 + 详情面板

#### Task 5.4.1: TaskDetail 页面集成

**修改文件**: `frontend/src/pages/TaskDetail.tsx`

**添加内容**:
- 新增"执行流程"标签页
- 显示该任务的 Agent 协作 DAG

#### Task 5.4.2: 节点详情抽屉

**实现要点**:
- 点击节点弹出详情面板
- 显示 Agent 详细信息（状态、模型、最近活动）
- 使用 Modal 或 Slide-over 组件

### 5.5 Day 4-5 验证

- [ ] 流程图正确渲染
- [ ] 节点位置布局合理
- [ ] 状态变化实时更新
- [ ] 消息传递有动画
- [ ] 暗色主题下样式正确
- [ ] 缩放/平移流畅

---

## 6. 性能监控图表 (Day 6)

### 6.1 上午: 后端 Metrics API + Recharts 基础

#### Task 6.1.1: 后端 Metrics API

**文件**:
- `backend/agent_forge/api/routes/metrics.py`
- `backend/agent_forge/core/metrics_service.py`

**端点**:
```
GET /api/v1/metrics/tasks?range=24h
GET /api/v1/metrics/agents?range=24h
GET /api/v1/metrics/tokens?range=24h
```

**实现要点**:
- 从数据库查询性能数据
- 支持时间范围过滤（1h/24h/7d）
- 返回图表所需格式
- JWT 认证保护

**数据聚合**:
- 任务执行时间：按小时聚合平均执行时间
- Agent 调用次数：按 Agent 聚合调用次数
- Token 消耗：按小时聚合 input/output tokens

#### Task 6.1.2: Recharts 基础图表组件

**文件**:
- `frontend/src/components/charts/TaskDurationChart.tsx`
- `frontend/src/components/charts/AgentCallsChart.tsx`

**实现要点**:
- 配置 Recharts 主题色（适配暗色/亮色）
- 实现基础 LineChart 和 BarChart
- 响应式布局

### 6.2 下午: Dashboard 集成 + 时间范围切换

#### Task 6.2.1: Dashboard 图表集成

**修改文件**: `frontend/src/pages/Dashboard.tsx`

**添加内容**:
- 任务执行时间趋势图（LineChart）
- Agent 调用分布图（BarChart）
- 统计卡片与图表布局

**布局**:
```
[统计卡片行]  [统计卡片行]  [统计卡片行]
[任务执行时间趋势]      [Agent调用分布]
[最近任务列表]          [Agent状态列表]
```

#### Task 6.2.2: 时间范围切换

**实现要点**:
- 添加时间范围选择器（1h/24h/7d）
- 切换时重新请求数据
- Loading 状态

### 6.3 Day 6 验证

- [ ] Dashboard 展示至少 2 种图表
- [ ] 图表数据来自后端 API
- [ ] 支持时间范围切换
- [ ] 暗色/亮色主题下样式正确
- [ ] 响应式布局

---

## 7. 联调 + 测试 (Day 7)

### 7.1 上午: 全面联调

**检查清单**:
- [ ] 主题切换 + 流程图：暗色/亮色下流程图样式正确
- [ ] 主题切换 + 图表：暗色/亮色下图表样式正确
- [ ] 登录 + 路由守卫：未登录无法访问受保护页面
- [ ] 登录 + 流程图：登录后可查看流程图
- [ ] 组件 + Toast：所有操作有适当的 Toast 反馈
- [ ] Modal + 主题：Modal 在两种主题下样式正确

### 7.2 下午: 补充测试 + UI 打磨

#### 7.2.1 补充测试

**前端测试**:
- Modal 组件测试
- Loading 组件测试
- Toast 组件测试
- Button 组件测试
- useTheme Hook 测试
- Login 页面测试
- ProtectedRoute 测试

**后端测试**:
- Metrics API 测试
- 任务流程图 API 测试

#### 7.2.2 UI 打磨

**打磨清单**:
- [ ] 所有页面暗色/亮色主题检查
- [ ] 移动端响应式检查
- [ ] Loading 状态统一处理
- [ ] 错误状态统一处理（Toast）
- [ ] 动画性能检查（避免卡顿）
- [ ] 焦点管理检查（可访问性）

#### 7.2.3 性能优化

**优化点**:
- React Flow 大数据量性能（节点 > 50）
- Recharts 数据点过多时的性能
- framer-motion 动画性能

### 7.3 Day 7 验证

- [ ] 所有验收标准通过
- [ ] 构建成功（npm run build）
- [ ] 无 TypeScript 错误
- [ ] 测试通过
- [ ] 暗色/亮色主题全面检查通过

---

## 8. 文件清单汇总

### 8.1 新增文件

```
frontend/src/
├── components/
│   ├── ui/
│   │   ├── Modal.tsx              # Day 1
│   │   ├── Loading.tsx            # Day 1
│   │   ├── Toast.tsx              # Day 1
│   │   ├── ToastContainer.tsx     # Day 1
│   │   └── Button.tsx             # Day 1
│   ├── flow/
│   │   ├── AgentFlow.tsx          # Day 4
│   │   ├── AgentNode.tsx          # Day 4
│   │   └── layout.ts              # Day 4
│   ├── charts/
│   │   ├── TaskDurationChart.tsx  # Day 6
│   │   └── AgentCallsChart.tsx    # Day 6
│   └── auth/
│       └── ProtectedRoute.tsx     # Day 3
├── hooks/
│   ├── useTheme.ts                # Day 2
│   └── useToast.ts                # Day 1
├── pages/
│   ├── Login.tsx                  # Day 3
│   └── Register.tsx               # Day 3
└── types/
    └── flow.ts                    # Day 4

backend/agent_forge/
├── api/routes/
│   └── metrics.py                 # Day 6
└── core/
    └── metrics_service.py         # Day 6
```

### 8.2 修改文件

```
frontend/src/
├── App.tsx                        # Day 3: 添加路由守卫
├── index.css                      # Day 2: 主题变量
├── pages/
│   ├── Dashboard.tsx              # Day 6: 添加图表
│   ├── AgentMonitor.tsx           # Day 4-5: 添加流程图标签
│   ├── TaskDetail.tsx             # Day 5: 添加流程图标签
│   └── Settings.tsx               # Day 2: 主题切换
└── stores/
    └── authStore.ts               # Day 3: 如有需要微调

backend/agent_forge/
├── api/routes/
│   └── tasks.py                   # Day 4: 添加 /{id}/flow 端点
└── main.py                        # Day 6: 注册 metrics 路由
```

---

## 9. 风险缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| React Flow 暗色主题适配困难 | 中 | 提前在 Day 4 上午验证主题适配 |
| Recharts 暗色主题适配困难 | 中 | 使用条件渲染或 CSS 变量控制颜色 |
| 主题切换 FOUC | 低 | 在 `<html>` 标签上预置主题类 |
| 路由守卫导致无限重定向 | 高 | 仔细测试登录/未登录状态切换 |
| framer-motion 与 React Flow 动画冲突 | 低 | 分别测试，必要时禁用 framer-motion 的 layout 动画 |
| 性能图表数据量大时卡顿 | 中 | 后端数据聚合，限制数据点数量 |

---

## 附录: 验收标准汇总

### 基础 UI 组件
- [ ] Modal 可打开/关闭，支持 ESC 和点击遮罩关闭，有动画
- [ ] Loading 有 3 种变体，可正确显示
- [ ] Toast 显示后自动关闭，支持同时多个，有动画
- [ ] Button 有 4 种变体，支持 loading 状态，有点击动画

### 主题系统
- [ ] 可在 暗色/亮色/跟随系统 之间切换
- [ ] 切换时无闪烁
- [ ] 偏好持久化（刷新后保持）
- [ ] 所有页面适配两种主题

### 登录/注册
- [ ] 可独立访问 /login 和 /register
- [ ] 表单有客户端校验
- [ ] 登录成功后跳转原页面
- [ ] 未登录访问受保护路由重定向到登录页
- [ ] Token 自动附加到 API 请求

### 流程图
- [ ] 可展示静态 Agent 协作 DAG
- [ ] 节点颜色随状态变化
- [ ] 支持缩放、平移
- [ ] 暗色主题下样式正确

### 性能图表
- [ ] Dashboard 展示至少 2 种图表
- [ ] 图表数据来自后端 API
- [ ] 支持时间范围切换
- [ ] 暗色主题下样式正确
