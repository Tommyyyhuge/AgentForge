# Week 4 设计文档：协作流程图 + UI 打磨

> **版本**: 1.0
> **日期**: 2026-05-21
> **基于**: Week 3 完成的基础设施 + 核心引擎
> **目标**: 实现 Agent 协作流程图可视化、性能监控图表、UI 组件库、主题系统、登录/注册
> **核心原则**: 基础设施先行、增量交付、测试驱动

---

## 目录

1. [概述](#1-概述)
2. [基础 UI 组件库](#2-基础-ui-组件库)
3. [主题系统](#3-主题系统)
4. [登录/注册 + 路由守卫](#4-登录注册--路由守卫)
5. [Agent 协作流程图](#5-agent-协作流程图)
6. [性能监控图表](#6-性能监控图表)
7. [API 设计](#7-api-设计)
8. [测试策略](#8-测试策略)
9. [验收标准](#9-验收标准)
10. [实施计划](#10-实施计划)

---

## 1. 概述

### 1.1 Week 4 目标

在 Week 3 基础设施之上，构建高级可视化功能和用户体验：

- **基础 UI 组件库**（Modal、Loading、Toast、Button）
- **主题系统**（暗色/亮色/跟随系统）
- **登录/注册独立页面** + 路由守卫
- **Agent 协作流程图**（静态 DAG + 实时监控）
- **性能监控图表**（Dashboard 增强）

### 1.2 技术选型

| 功能 | 技术 | 理由 |
|------|------|------|
| 流程图 | React Flow | 专业节点图库，支持拖拽/缩放/暗色主题 |
| 性能图表 | Recharts | React 生态最流行，声明式 API |
| 主题切换 | Tailwind CSS dark mode | 与现有样式体系一致 |
| 状态持久化 | Zustand persist | 与现有 stores 一致 |
| 动画 | Framer Motion | React 生态标准动画库，用于 Modal/Toast/Button/流程图节点动画 |

### 1.3 与 Week 3 的衔接

```
Week 3 基础:
├── api/client.ts         → Week 4 登录/注册调用
├── stores/authStore.ts   → Week 4 路由守卫 + 持久化
├── stores/taskStore.ts   → Week 4 性能数据
├── stores/agentStore.ts  → Week 4 流程图数据源
├── pages/Dashboard.tsx   → Week 4 增强图表
├── pages/AgentMonitor.tsx → Week 4 流程图嵌入
├── pages/Settings.tsx    → Week 4 主题切换
└── index.css             → Week 4 主题变量扩展

Week 4 新增:
├── components/ui/Modal.tsx       # 模态对话框
├── components/ui/Loading.tsx     # 加载状态
├── components/ui/Tooltip.tsx     # 提示信息
├── components/ui/Toast.tsx       # 通知消息
├── components/flow/AgentFlow.tsx # 流程图组件
├── components/charts/PerformanceChart.tsx # 性能图表
├── pages/Login.tsx               # 登录页面
├── pages/Register.tsx            # 注册页面
├── hooks/useTheme.ts             # 主题 Hook
└── api/routes/metrics.py         # 性能指标 API
```

---

## 2. 基础 UI 组件库

### 2.1 设计原则

- **一致性**: 所有组件使用 Tailwind CSS 样式，与现有设计体系一致
- **可访问性**: 支持键盘导航、ARIA 属性
- **可组合性**: 组件接受 children 和 className 扩展

### 2.2 Modal 对话框

**文件**: `components/ui/Modal.tsx`

**功能**:
- 创建任务对话框
- 确认操作对话框（删除、取消）
- 信息展示对话框

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
}
```

**特性**:
- 点击遮罩层关闭（可配置）
- ESC 键关闭
- 打开时锁定背景滚动
- 进入/退出动画（fade + scale）
- 聚焦管理（自动聚焦第一个可交互元素）

### 2.3 Loading 加载态

**文件**: `components/ui/Loading.tsx`

**变体**:
- **Spinner**: 转圈加载（按钮内、小区域）
- **Skeleton**: 骨架屏（页面初始加载）
- **Overlay**: 全屏遮罩（提交表单、切换页面）

**Props**:
```typescript
interface LoadingProps {
  variant: 'spinner' | 'skeleton' | 'overlay'
  text?: string
  className?: string
}
```

### 2.4 Toast 通知

**文件**: `components/ui/Toast.tsx` + `components/ui/ToastContainer.tsx`

**功能**:
- 成功/错误/警告/信息 四种类型
- 自动关闭（可配置时长）
- 点击关闭
- 同时显示多个 Toast
- 进入/退出动画（slide + fade）

**API**:
```typescript
interface ToastOptions {
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  duration?: number  // 默认 3000ms
}

// 使用方式
toast.success('任务创建成功')
toast.error('操作失败，请重试')
```

### 2.5 Button 按钮

**文件**: `components/ui/Button.tsx`

**功能**:
- 统一项目所有按钮样式
- 支持多种变体：primary、secondary、ghost、danger
- 支持加载状态（内置 Loading spinner）
- 支持图标前缀/后缀

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

**为什么需要统一 Button**：
目前项目使用 `.forge-btn-primary` 等 CSS 类，但缺乏统一的 React 组件。统一 Button 组件可以：
- 内置 loading 状态（无需外部判断）
- 统一禁用/加载样式
- 支持 framer-motion 点击动画

---

## 3. 主题系统

### 3.1 设计目标

- 支持 **暗色** / **亮色** / **跟随系统** 三种模式
- 切换时无闪烁（避免 FOUC）
- 用户偏好持久化（localStorage）
- 所有组件自动响应主题变化

### 3.2 实现方案

**技术**: Tailwind CSS `dark` 类策略

**CSS 变量扩展** (`index.css`):
```css
@layer base {
  :root {
    /* 亮色主题变量 */
    --surface-bg: #ffffff;
    --surface-light: #f8fafc;
    --surface-border: #e2e8f0;
    --text-primary: #0f172a;
    --text-secondary: #475569;
    /* ... */
  }
  
  .dark {
    /* 暗色主题变量（现有） */
    --surface-bg: #0a0a0a;
    --surface-light: #141414;
    --surface-border: #262626;
    --text-primary: #fafafa;
    --text-secondary: #a3a3a3;
    /* ... */
  }
}
```

**Hook** (`hooks/useTheme.ts`):
```typescript
type Theme = 'light' | 'dark' | 'system'

interface ThemeState {
  theme: Theme
  resolvedTheme: 'light' | 'dark'  // 实际应用的主题
  setTheme: (theme: Theme) => void
}
```

**关键逻辑**:
1. 初始化时读取 localStorage 中的主题偏好
2. `system` 模式监听 `prefers-color-scheme` 媒体查询
3. 切换时立即更新 `<html>` 元素的 `class`（`dark` 或 `light`）
4. Tailwind 的 `dark:` 前缀自动响应

### 3.3 组件适配

所有现有组件需要检查并适配：
- 背景色：使用 `bg-surface-bg` 而非硬编码
- 文字色：使用 `text-text-primary` 而非 `text-white`
- 边框色：使用 `border-surface-border`
- Tailwind 的 `dark:` 前缀作为兜底

---

## 4. 登录/注册 + 路由守卫

### 4.1 页面设计

**文件**: `pages/Login.tsx` + `pages/Register.tsx`

**布局**:
- 居中卡片式布局
- 左侧：品牌信息 + 简介（大屏显示）
- 右侧：表单区域
- 暗色/亮色主题自适应

**登录表单**:
- 用户名输入框
- 密码输入框（显示/隐藏切换）
- "记住我"选项
- 登录按钮（Loading 状态）
- 错误提示（Toast）
- "没有账号？去注册"链接

**注册表单**:
- 用户名输入框（实时校验：长度、字符限制）
- 邮箱输入框（格式校验）
- 密码输入框（强度提示）
- 确认密码输入框（一致性校验）
- 注册按钮
- "已有账号？去登录"链接

### 4.2 路由守卫

**文件**: `components/auth/ProtectedRoute.tsx`

**实现**:
```typescript
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  const location = useLocation()
  
  if (isLoading) return <Loading variant="overlay" />
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} />
  
  return children
}
```

**路由配置** (`App.tsx`):
```typescript
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/register" element={<Register />} />
  <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
  {/* ...其他受保护路由 */}
</Routes>
```

### 4.3 与后端集成

- 调用现有 `/api/v1/auth/register` 和 `/api/v1/auth/login` API
- 使用现有 `authStore` 的 `login` / `register` actions
- Token 自动附加（`api/client.ts` 拦截器已实现）

---

## 5. Agent 协作流程图

### 5.1 设计目标

- **静态 DAG 预览**：展示任务规划的 Agent 调用顺序和依赖关系
- **实时监控视图**：展示执行中的 Agent 状态和消息传递
- **交互性**：支持缩放、平移、点击查看详情
- **暗色主题适配**：与整体 UI 风格一致

### 5.2 数据结构

**节点（Node）**:
```typescript
interface AgentNode {
  id: string           // agent-1
  type: 'agent'
  data: {
    name: string       // Prometheus
    role: AgentRole    // orchestrator
    status: AgentStatus // idle/thinking/executing/completed/error
    description: string
    model: string
  }
  position: { x: number; y: number }
}
```

**边（Edge）**:
```typescript
interface AgentEdge {
  id: string           // e-agent-1-agent-2
  source: string       // agent-1
  target: string       // agent-2
  type: 'default' | 'animated'
  data?: {
    messageType: 'assignment' | 'result' | 'feedback'
    label?: string
  }
  animated: boolean    // 消息传递时动画
}
```

### 5.3 静态 DAG 预览

**场景**: 用户创建任务后，展示规划出的 Agent 协作流程

**布局算法**:
- 使用 **分层布局**（Layered Layout）
- Orchestrator 在顶层
- 依赖关系决定层次
- 同层节点水平分布

**实现**:
```typescript
// 从任务的 assignedAgents 和 dependencies 生成节点和边
function buildTaskDAG(task: Task, agents: Agent[]): { nodes: AgentNode[]; edges: AgentEdge[] }
```

### 5.4 实时监控视图

**场景**: 任务执行过程中，实时显示 Agent 状态变化和消息传递

**特性**:
- 节点颜色随状态变化（idle→灰色, thinking→蓝色, executing→黄色, completed→绿色, error→红色）
- 消息传递时边线动画（脉冲效果）
- 点击节点查看 Agent 详情（抽屉面板）
- 时间线回放（执行完成后可回放整个过程）

**数据源**:
- SSE 实时推送 Agent 状态更新
- 现有 `agentStore.subscribeToAgents()`

### 5.5 自定义节点样式

**React Flow 自定义节点**:
```tsx
function AgentFlowNode({ data }: NodeProps<AgentNodeData>) {
  const statusColor = AGENT_STATUS_COLORS[data.status]
  return (
    <div className={`forge-flow-node ${statusColor}`}>
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
    </div>
  )
}
```

### 5.6 页面集成

**AgentMonitor 页面增强**:
- 顶部：统计卡片（现有）
- 中部：流程图视图（新增标签页切换：列表视图 / 流程图视图）
- 底部：Agent 列表（现有）

**TaskDetail 页面增强**:
- 新增"执行流程"标签页
- 显示该任务的 Agent 协作 DAG

---

## 6. 性能监控图表

### 6.1 设计目标

- **Dashboard 增强**：将现有统计卡片升级为实时图表
- **关键指标可视化**：任务吞吐量、Agent 调用延迟、LLM Token 消耗
- **时间范围**：支持 1小时/24小时/7天 切换

### 6.2 图表类型

| 指标 | 图表类型 | 数据源 |
|------|----------|--------|
| 任务执行时间趋势 | 折线图 (LineChart) | 任务完成时间 |
| Agent 调用次数分布 | 柱状图 (BarChart) | Agent 执行记录 |
| 任务状态分布 | 饼图 (PieChart) | 任务状态统计 |
| LLM Token 消耗趋势 | 面积图 (AreaChart) | LLM 调用记录 |
| 系统资源使用 | 仪表盘 (Gauge) | CPU/内存 |

### 6.3 Dashboard 布局增强

**现有布局**:
```
[统计卡片行]  [统计卡片行]  [统计卡片行]
[最近任务列表]          [Agent状态列表]
```

**增强后布局**:
```
[统计卡片行]  [统计卡片行]  [统计卡片行]
[任务执行时间趋势]      [Agent调用分布]
[任务状态饼图]          [Token消耗趋势]
[最近任务列表]          [Agent状态列表]
```

### 6.4 后端 API

**新增端点**:
```
GET /api/v1/metrics/tasks?range=24h
→ { timestamps: string[], durations: number[], counts: number[] }

GET /api/v1/metrics/agents?range=24h
→ { agentId: string, calls: number, avgDuration: number }[]

GET /api/v1/metrics/tokens?range=24h
→ { timestamps: string[], inputTokens: number[], outputTokens: number[] }
```

**数据存储**:
- 使用现有 `PerformanceMetric` ORM 模型
- 定时任务汇总（每 5 分钟）
- 保留 30 天历史数据

---

## 7. API 设计

### 7.1 新增 API

| 端点 | 方法 | 描述 | 认证 |
|------|------|------|------|
| `/api/v1/metrics/tasks` | GET | 任务性能指标 | ✅ JWT |
| `/api/v1/metrics/agents` | GET | Agent 调用指标 | ✅ JWT |
| `/api/v1/metrics/tokens` | GET | Token 消耗指标 | ✅ JWT |
| `/api/v1/tasks/{id}/flow` | GET | 任务流程图数据 | ✅ JWT |

### 7.2 数据模型

**任务流程图响应**:
```json
{
  "nodes": [
    {
      "id": "agent-1",
      "type": "agent",
      "data": {
        "name": "Prometheus",
        "role": "orchestrator",
        "status": "executing"
      },
      "position": { "x": 100, "y": 100 }
    }
  ],
  "edges": [
    {
      "id": "e-1-2",
      "source": "agent-1",
      "target": "agent-2",
      "animated": true
    }
  ]
}
```

---

## 8. 测试策略

### 8.1 前端测试

**组件测试**:
- Modal: 打开/关闭、ESC 键、点击遮罩、焦点管理
- Loading: 各变体渲染
- Tooltip: 悬停显示、方向、延迟
- Toast: 显示/自动关闭、多个 Toast、类型

**Hook 测试**:
- useTheme: 初始化、切换、持久化、系统模式

**页面测试**:
- Login: 表单校验、提交、错误处理
- Register: 密码强度、确认密码、邮箱格式
- ProtectedRoute: 未登录重定向、已登录放行

### 8.2 后端测试

**新增测试文件**:
- `tests/unit/test_metrics_api.py`
- `tests/unit/test_task_flow.py`

**测试覆盖**:
- 性能指标 API 返回正确格式
- 时间范围过滤有效
- 权限控制（JWT 验证）
- 任务流程图数据生成正确

---

## 9. 验收标准

### 9.1 基础 UI 组件

- [ ] Modal 可打开/关闭，支持 ESC 和点击遮罩关闭，有动画
- [ ] Loading 有 3 种变体，可正确显示
- [ ] Toast 显示后自动关闭，支持同时多个，有动画
- [ ] Button 有 4 种变体，支持 loading 状态，有点击动画

### 9.2 主题系统

- [ ] 可在 暗色/亮色/跟随系统 之间切换
- [ ] 切换时无闪烁
- [ ] 偏好持久化（刷新后保持）
- [ ] 所有页面适配两种主题

### 9.3 登录/注册

- [ ] 可独立访问 /login 和 /register
- [ ] 表单有客户端校验
- [ ] 登录成功后跳转原页面
- [ ] 未登录访问受保护路由重定向到登录页
- [ ] Token 自动附加到 API 请求

### 9.4 流程图

- [ ] 可展示静态 Agent 协作 DAG
- [ ] 节点颜色随状态变化
- [ ] 支持缩放、平移
- [ ] 暗色主题下样式正确

### 9.5 性能图表

- [ ] Dashboard 展示至少 2 种图表
- [ ] 图表数据来自后端 API
- [ ] 支持时间范围切换
- [ ] 暗色主题下样式正确

---

## 10. 实施计划

### Day 0: 安装依赖

**任务**:
```bash
cd frontend
npm install reactflow recharts framer-motion
```

**验证**:
- `package.json` 包含所有新依赖
- `npm run build` 成功

### Day 1: 基础 UI 组件

**上午**:
- Modal 组件（framer-motion 进入/退出动画）
- Loading 组件

**下午**:
- Toast 组件 + ToastContainer（framer-motion slide动画）
- Button 组件（framer-motion 点击缩放）

**验证**:
- 各组件可独立渲染
- 交互行为正确
- 动画流畅

### Day 2: 主题系统

**上午**:
- CSS 变量扩展
- useTheme Hook

**下午**:
- 现有组件适配
- Settings 页面集成主题切换

**验证**:
- 切换无闪烁
- 持久化工作

### Day 3: 登录/注册 + 路由守卫

**上午**:
- Login 页面
- Register 页面

**下午**:
- ProtectedRoute 组件
- App.tsx 路由配置更新

**验证**:
- 登录流程完整
- 路由守卫生效

### Day 4-5: Agent 协作流程图

**Day 4 上午**:
- React Flow 安装 + 基础配置
- 自定义 Agent 节点

**Day 4 下午**:
- DAG 布局算法
- 静态流程图展示

**Day 5 上午**:
- 实时状态更新
- 消息传递动画

**Day 5 下午**:
- AgentMonitor 页面集成
- TaskDetail 页面集成

**验证**:
- 流程图正确渲染
- 状态变化实时更新

### Day 6: 性能监控图表

**上午**:
- Recharts 安装 + 基础图表
- 后端 Metrics API

**下午**:
- Dashboard 图表集成
- 时间范围切换

**验证**:
- 图表数据正确
- 交互正常

### Day 7: 联调 + 测试 + 打磨

**上午**:
- 所有功能联调
- 暗色/亮色主题全面检查

**下午**:
- 补充测试
- UI 细节打磨
- 性能优化

**验证**:
- 所有验收标准通过
- 构建成功
- 无 TypeScript 错误

---

## 附录 A: 依赖清单

### 新增前端依赖

```json
{
  "dependencies": {
    "reactflow": "^11.x",
    "recharts": "^2.x",
    "framer-motion": "^11.x"
  }
}
```

### 安装命令

```bash
cd frontend
npm install reactflow recharts framer-motion
```

### Framer Motion 使用场景

| 组件 | 动画效果 | 实现方式 |
|------|----------|----------|
| Modal | 淡入 + 缩放 | `<AnimatePresence>` + `motion.div` |
| Toast | 滑入 + 淡出 | `<AnimatePresence>` + `motion.div` |
| Button | 点击缩放 | `motion.button` + `whileTap` |
| 流程图节点 | 状态变化过渡 | `motion.div` + `layout` |
| 页面切换 | 淡入淡出 | `<AnimatePresence>` + `motion.div` |

---

## 附录 B: 文件清单

### 新增文件

```
frontend/src/
├── components/
│   ├── ui/
│   │   ├── Modal.tsx
│   │   ├── Loading.tsx
│   │   ├── Toast.tsx
│   │   ├── ToastContainer.tsx
│   │   └── Button.tsx
│   ├── flow/
│   │   ├── AgentFlow.tsx
│   │   ├── AgentNode.tsx
│   │   └── layout.ts
│   └── charts/
│       ├── TaskDurationChart.tsx
│       ├── AgentCallsChart.tsx
│       └── TokenUsageChart.tsx
├── components/auth/
│   └── ProtectedRoute.tsx
├── hooks/
│   └── useTheme.ts
├── pages/
│   ├── Login.tsx
│   └── Register.tsx
└── types/
    └── flow.ts

backend/agent_forge/
├── api/routes/
│   └── metrics.py
└── core/
    └── metrics_service.py
```

### 修改文件

```
frontend/src/
├── App.tsx                    # 添加路由守卫
├── index.css                  # 主题变量
├── pages/
│   ├── Dashboard.tsx          # 添加图表
│   ├── AgentMonitor.tsx       # 添加流程图标签
│   ├── TaskDetail.tsx         # 添加流程图标签
│   └── Settings.tsx           # 主题切换
└── stores/
    └── authStore.ts           # 如有需要微调
```
