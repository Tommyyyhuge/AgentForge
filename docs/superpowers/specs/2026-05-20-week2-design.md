# Week 2 设计文档：多 Agent 调度 + 前端骨架

> **版本**: 1.0
> **日期**: 2026-05-20
> **基于**: Week 1 完成的基础设施 + 核心引擎
> **目标**: 实现多 Agent 协作调度系统和前端应用骨架

---

## 目录

1. [概述](#1-概述)
2. [后端模块设计](#2-后端模块设计)
3. [前端模块设计](#3-前端模块设计)
4. [数据流设计](#4-数据流设计)
5. [API 设计](#5-api-设计)
6. [测试策略](#6-测试策略)
7. [验收标准](#7-验收标准)
8. [风险评估](#8-风险评估)

---

## 1. 概述

### 1.1 目标

Week 2 在 Week 1 基础设施之上，构建多 Agent 协作调度能力：

- **Planner**: 任务拆解为可执行的子任务依赖图
- **Orchestrator**: 按依赖图调度 Agent 执行（并行/串行、超时、取消）
- **6 个 Agent 角色**: 每个角色有独特的能力和目标
- **A2A 总线**: Agent 间通信基础设施
- **前端骨架**: 可交互的 Web 应用基础

### 1.2 依赖关系

```
Week 1 基础:
├── config/settings.py
├── models/schemas.py
├── core/llm_client.py
├── core/react_loop.py
├── core/cancellation.py
├── tools/base.py
├── mcp/tool_registry.py
└── agents/base.py

Week 2 构建:
├── core/planner.py         (依赖: llm_client, schemas)
├── core/orchestrator.py    (依赖: planner, agents, a2a_bus)
├── core/a2a_bus.py         (依赖: schemas)
├── agents/*_agent.py       (依赖: base, react_loop, tools)
├── agents/factory.py       (依赖: all agents)
└── frontend/               (独立，通过 API 对接)
```

### 1.3 新增文件清单

**后端 (12 个文件)**:
- `core/planner.py`
- `core/orchestrator.py`
- `core/a2a_bus.py`
- `agents/planner_agent.py`
- `agents/researcher_agent.py`
- `agents/coder_agent.py`
- `agents/writer_agent.py`
- `agents/reviewer_agent.py`
- `agents/executor_agent.py`
- `agents/factory.py`
- `api/routes/tasks.py`
- `api/routes/agents.py`

**前端 (10+ 个文件)**:
- `src/main.tsx` (更新)
- `src/App.tsx` (更新)
- `src/stores/authStore.ts`
- `src/stores/taskStore.ts`
- `src/stores/agentStore.ts`
- `src/stores/uiStore.ts`
- `src/api/client.ts`
- `src/pages/Dashboard.tsx`
- `src/pages/Tasks.tsx`
- `src/pages/Agents.tsx`
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/Header.tsx`

---

## 2. 后端模块设计

### 2.1 规划器 (Planner)

**文件**: `core/planner.py`

**职责**: 将自然语言任务拆解为结构化的子任务依赖图

**核心类**:

```python
class PlanNode:
    """计划节点"""
    id: str
    description: str
    dependencies: List[str]
    estimated_duration: Optional[int]
    assigned_role: Optional[AgentRole]
    status: TaskStatus

class PlanGraph:
    """计划依赖图"""
    nodes: Dict[str, PlanNode]
    root_node_id: str
    
    def get_execution_order(self) -> List[List[str]]:
        """返回分层执行顺序（同一层可并行）"""
        
    def validate_no_cycles(self) -> bool:
        """检测循环依赖"""

class Planner:
    """任务规划器"""
    
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
    
    async def plan(self, task_description: str) -> PlanGraph:
        """将任务拆解为计划图"""
        # 1. 构建规划提示
        # 2. 调用 LLM
        # 3. 解析响应（支持 3 种格式）
        # 4. 构建依赖图
        # 5. 验证无循环
        # 6. 返回 PlanGraph
    
    def _parse_plan_response(self, content: str) -> PlanGraph:
        """解析 LLM 响应（3 种策略）"""
        # 策略 1: 严格 JSON
        # 策略 2: 宽松 JSON（容错）
        # 策略 3: 自然语言回退
```

**规划提示模板**:

```
你是一个任务规划专家。请将以下任务拆解为子任务，并明确依赖关系。

任务: {task_description}

请按以下 JSON 格式输出:
{
    "nodes": [
        {
            "id": "step-1",
            "description": "子任务描述",
            "dependencies": [],
            "estimated_duration": 60,
            "assigned_role": "researcher"
        }
    ]
}

规则:
1. 每个子任务应原子化（不可再分）
2. 依赖关系必须形成有向无环图（DAG）
3. 为每个子任务建议最合适的 Agent 角色
4. 预估每个子任务的执行时间（秒）
```

---

### 2.2 调度器 (Orchestrator)

**文件**: `core/orchestrator.py`

**职责**: 按依赖图调度 Agent 执行，管理生命周期

**核心类**:

```python
class Orchestrator:
    """任务调度器"""
    
    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        max_concurrency: int = 3
    ):
        self.llm_router = llm_router
        self.tool_registry = tool_registry
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.agents: Dict[AgentRole, BaseAgent] = {}
    
    async def execute_plan(
        self,
        plan: PlanGraph,
        cancellation_token: Optional[CancellationToken] = None
    ) -> AsyncGenerator[AgentStep, None]:
        """执行计划图"""
        # 1. 拓扑排序，获取分层执行顺序
        # 2. 逐层执行（同层并行）
        # 3. 使用信号量控制并发
        # 4. 每个子任务设置超时
        # 5. 检查取消状态
        # 6. 聚合结果
    
    async def _execute_node(
        self,
        node: PlanNode,
        cancellation_token: Optional[CancellationToken]
    ) -> TaskResult:
        """执行单个节点"""
        # 1. 根据角色获取/创建 Agent
        # 2. 构建 Task 对象
        # 3. 调用 Agent.execute()
        # 4. 设置超时
        # 5. 返回结果
    
    def _get_or_create_agent(self, role: AgentRole) -> BaseAgent:
        """获取或创建 Agent 实例"""
```

**执行流程**:

```
PlanGraph
├── Layer 1: [Node A, Node B]      -> 并行执行（信号量控制）
├── Layer 2: [Node C]              -> 等待 A, B 完成
├── Layer 3: [Node D, Node E]      -> 等待 C 完成，D 和 E 并行
└── Layer 4: [Node F]              -> 等待 D, E 完成
```

**超时策略**:
- 任务级超时：单个节点执行超时（默认 120 秒）
- 计划级超时：整个计划执行超时（默认 600 秒）

---

### 2.3 A2A 总线

**文件**: `core/a2a_bus.py`

**职责**: Agent 间异步通信基础设施

**核心类**:

```python
class A2AMessage:
    """A2A 消息"""
    id: str
    sender_id: str
    receiver_id: Optional[str]
    message_type: str
    content: str
    correlation_id: Optional[str]
    timestamp: datetime

class A2ABus:
    """A2A 消息总线"""
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._history: List[A2AMessage] = []
        self._max_history = 1000
    
    async def register(self, agent_id: str):
        """注册 Agent 到总线"""
        self._queues[agent_id] = asyncio.Queue()
    
    async def unregister(self, agent_id: str):
        """从总线注销 Agent"""
        del self._queues[agent_id]
    
    async def send(self, message: A2AMessage):
        """发送点对点消息"""
        if message.receiver_id in self._queues:
            await self._queues[message.receiver_id].put(message)
            self._add_to_history(message)
    
    async def broadcast(self, message: A2AMessage):
        """广播消息给所有 Agent"""
        for agent_id, queue in self._queues.items():
            if agent_id != message.sender_id:
                await queue.put(message)
        self._add_to_history(message)
    
    async def request_response(
        self,
        request: A2AMessage,
        timeout: float = 30.0
    ) -> Optional[A2AMessage]:
        """请求-响应模式"""
        correlation_id = str(uuid.uuid4())
        request.correlation_id = correlation_id
        await self.send(request)
        
        try:
            return await asyncio.wait_for(
                self._wait_for_response(correlation_id),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None
    
    async def receive(self, agent_id: str) -> A2AMessage:
        """接收消息（阻塞）"""
        return await self._queues[agent_id].get()
    
    def _add_to_history(self, message: A2AMessage):
        """添加到历史，自动清理"""
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
```

---

### 2.4 Agent 角色实现

**文件**: `agents/*_agent.py`, `agents/factory.py`

**设计原则**:
- 每个 Agent 继承 `BaseAgent`
- 通过 `get_system_prompt()` 定义角色行为
- 通过 `tools` 属性定义可用工具
- 通过 `role` 类属性标识角色

**Agent 列表**:

| Agent | 职责 | 特色工具 |
|-------|------|---------|
| PlannerAgent | 任务规划 | - |
| ResearcherAgent | 信息收集 | WebSearchTool |
| CoderAgent | 代码生成 | CodeExecuteTool |
| WriterAgent | 文档撰写 | SummarizeTool |
| ReviewerAgent | 质量审查 | - |
| ExecutorAgent | 通用执行 | 所有工具 |

**AgentFactory**:

```python
class AgentFactory:
    _registry: Dict[AgentRole, Type[BaseAgent]] = {
        AgentRole.PLANNER: PlannerAgent,
        AgentRole.RESEARCHER: ResearcherAgent,
        AgentRole.CODER: CoderAgent,
        AgentRole.WRITER: WriterAgent,
        AgentRole.REVIEWER: ReviewerAgent,
        AgentRole.EXECUTOR: ExecutorAgent,
    }
    
    @classmethod
    def create(cls, role: AgentRole, llm_router: LLMRouter) -> BaseAgent:
        agent_class = cls._registry[role]
        return agent_class(llm_router)
```

---

## 3. 前端模块设计

### 3.1 技术栈

- **框架**: React 18 + TypeScript
- **构建**: Vite
- **样式**: Tailwind CSS
- **路由**: React Router v6
- **状态**: Zustand
- **HTTP**: Axios + SSE

### 3.2 页面结构

```
/              -> Dashboard（首页，任务统计、Agent 状态）
/tasks         -> TaskList（任务列表）
/tasks/new     -> TaskCreate（创建任务）
/tasks/:id     -> TaskDetail（任务详情，含 ReAct 步骤可视化）
/agents        -> AgentMonitor（Agent 监控面板）
/chat          -> MultiAgentChat（多 Agent 协作聊天室）
/settings      -> Settings（设置）
```

### 3.3 Store 设计

**TaskStore**:

```typescript
interface TaskStore {
  tasks: Task[];
  currentTask: Task | null;
  steps: AgentStep[];
  isLoading: boolean;
  
  fetchTasks: () => Promise<void>;
  createTask: (description: string) => Promise<void>;
  fetchTaskDetail: (id: string) => Promise<void>;
  subscribeToTask: (id: string) => void;
}
```

**AgentStore**:

```typescript
interface AgentStore {
  agents: AgentState[];
  isLoading: boolean;
  
  fetchAgents: () => Promise<void>;
  subscribeToAgents: () => void;
}
```

---

## 4. 数据流设计

### 4.1 任务创建到执行完成

```
用户输入
  ->
Frontend: POST /api/tasks {description}
  ->
Backend: TaskRouter.create_task()
  ->
Orchestrator.execute_plan()
  -> Planner.plan() -> PlanGraph
  -> 逐层执行节点
     -> Agent.execute() -> ReActLoop.run()
        -> LLM 调用 + 工具执行
  -> 生成 AgentStep（SSE 推送）
  ->
Frontend: 接收 SSE 事件，更新 TaskStore
  ->
UI: 实时显示执行步骤
```

### 4.2 Agent 间通信

```
Agent A (Researcher)
  ->
A2ABus.send(Message {receiver: "Agent B", content: "..."})
  ->
Agent B (Writer) 接收消息
  ->
Agent B 处理并响应
  ->
A2ABus.send(Message {receiver: "Agent A", content: "..."})
```

---

## 5. API 设计

### 5.1 任务 API

```
POST   /api/v1/tasks              # 创建任务
GET    /api/v1/tasks              # 获取任务列表
GET    /api/v1/tasks/{id}         # 获取任务详情
DELETE /api/v1/tasks/{id}         # 取消任务
GET    /api/v1/tasks/{id}/stream  # SSE：任务执行实时流
```

### 5.2 Agent API

```
GET    /api/v1/agents             # 获取 Agent 列表
GET    /api/v1/agents/{id}        # 获取 Agent 详情
POST   /api/v1/agents/{id}/message  # 发送消息给 Agent
GET    /api/v1/agents/stream      # SSE：Agent 状态实时流
```

### 5.3 SSE 事件格式

```json
{
  "event": "step",
  "data": {
    "task_id": "task-123",
    "agent_id": "agent-456",
    "step_type": "thought",
    "content": "...",
    "timestamp": "2026-05-20T10:00:00Z"
  }
}
```

---

## 6. 测试策略

### 6.1 单元测试

| 模块 | 测试文件 | 关键测试点 |
|------|---------|-----------|
| Planner | `test_planner.py` | 解析 3 种格式、循环依赖检测、回退机制 |
| Orchestrator | `test_orchestrator.py` | 并行执行、超时、取消、依赖顺序 |
| A2A Bus | `test_a2a_bus.py` | 点对点、广播、请求-响应、历史清理 |
| Agents | `test_agents.py` | 6 个角色创建、工具集、提示词 |
| Factory | `test_factory.py` | 所有角色可创建、异常处理 |

### 6.2 集成测试

- 端到端任务执行：创建任务 -> 规划 -> 执行 -> 完成
- 多 Agent 协作：Researcher -> Writer -> Reviewer
- 取消流程：创建任务 -> 取消 -> 资源清理

---

## 7. 验收标准

### 7.1 功能验收

- [ ] Planner 可解析 3 种格式变体（严格 JSON、宽松 JSON、自然语言）
- [ ] Planner 能检测循环依赖并抛出明确错误
- [ ] Planner 解析失败时回退到单任务模式
- [ ] Orchestrator 能并行执行无依赖任务
- [ ] Orchestrator 能按序执行有依赖任务
- [ ] Orchestrator 超时后优雅退出并清理资源
- [ ] Orchestrator 取消后停止所有子任务
- [ ] 6 个 Agent 角色可独立创建和执行
- [ ] AgentFactory 能创建所有角色
- [ ] A2A 点对点消息可达
- [ ] A2A 广播消息可达
- [ ] A2A 请求-响应超时工作
- [ ] 前端 `npm run dev` 可正常启动
- [ ] 前端路由正常工作
- [ ] 前端 Tailwind 样式生效
- [ ] Zustand Stores 状态可更新和持久化

### 7.2 质量验收

- [ ] 后端测试覆盖率 > 80%
- [ ] 所有单元测试通过
- [ ] black + isort 格式化通过
- [ ] mypy 类型检查通过
- [ ] 前端 ESLint 无错误

---

## 8. 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| LLM 规划不稳定 | 高 | 中 | 3 种解析策略 + 回退机制 |
| 并发执行复杂 | 中 | 高 | 信号量控制 + 充分测试 |
| 前端状态管理复杂 | 中 | 中 | Zustand 简化 + 类型完整 |
| SSE 连接管理 | 低 | 中 | 心跳检测 + 自动重连 |

---

## 附录

### A. 执行顺序

```
Day 1: Planner + Orchestrator
Day 2: 6 个 Agent 角色
Day 3: A2A Bus + 后端 API 路由
Day 4: 前端骨架（路由 + 页面）
Day 5: Zustand Stores + API 对接
Day 6: 集成测试 + Bug 修复
Day 7: 文档 + 验收
```

### B. 与 Week 3 的衔接

Week 3 将基于 Week 2 构建：
- Week 2 的 Agent -> Week 3 的工具集成（8 个 MCP 工具）
- Week 2 的 A2A Bus -> Week 3 的 Reflection 引擎
- Week 2 的前端骨架 -> Week 3 的完整页面功能
