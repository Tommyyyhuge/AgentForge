# Week 2 详细实施计划

> **版本**: 1.0
> **日期**: 2026-05-20
> **基于**: docs/superpowers/specs/2026-05-20-week2-adjusted-design.md
> **目标**: 文件级实施清单，包含代码结构、测试要点、依赖关系

---

## 目录

1. [执行策略](#1-执行策略)
2. [Day 1: Planner + ORM](#2-day-1-planner--orm)
3. [Day 2: Agent 角色](#3-day-2-agent-角色)
4. [Day 3: A2A Bus + 工具](#4-day-3-a2a-bus--工具)
5. [Day 4: 前端骨架](#5-day-4-前端骨架)
6. [Day 5: Orchestrator](#6-day-5-orchestrator)
7. [Day 6: API 路由 + 测试](#7-day-6-api-路由--测试)
8. [Day 7: 联调](#8-day-7-联调)
9. [并行执行建议](#9-并行执行建议)
10. [风险缓解](#10-风险缓解)

---

## 1. 执行策略

### 1.1 核心原则

- **依赖先行**：先实现被依赖的模块，再实现依赖方
- **接口契约**：模块间通过明确的接口契约通信
- **测试驱动**：每个模块先写测试，再写实现
- **渐进集成**：每完成一个模块立即集成测试

### 1.2 模块依赖图

```
Week 2 实施依赖图:

Day 1 ───────────────────────────────────────┐
├─ core/planner.py                            │
│   └─ 依赖: llm_client.py, schemas.py        │
│                                              │
└─ database/models.py                          │
    └─ 依赖: database/connection.py            │
                                              │
Day 2 ───────────────────────────────────────┤
├─ agents/executor_agent.py                   │
│   └─ 依赖: agents/base.py, react_loop.py   │
│                                              │
├─ agents/researcher_agent.py                 │
│   └─ 依赖: agents/base.py, react_loop.py   │
│                                              │
└─ agents/factory.py                          │
    └─ 依赖: executor_agent, researcher_agent│
                                              │
Day 3 ───────────────────────────────────────┤
├─ core/a2a_bus.py                            │
│   └─ 依赖: schemas.py                       │
│                                              │
├─ tools/web_search.py                        │
│   └─ 依赖: tools/base.py                    │
│                                              │
└─ tools/calculator.py                        │
    └─ 依赖: tools/base.py                    │
                                              │
Day 4 ───────────────────────────────────────┤
└─ frontend/                                  │
    └─ 独立，通过 API 对接                    │
                                              │
Day 5 ───────────────────────────────────────┤
└─ core/orchestrator.py                       │
    └─ 依赖: planner, agents, a2a_bus, tools  │
                                              │
Day 6 ───────────────────────────────────────┤
├─ api/routes/tasks.py                        │
│   └─ 依赖: orchestrator, models             │
│                                              │
├─ api/routes/agents.py                       │
│   └─ 依赖: a2a_bus, agents                  │
│                                              │
└─ tests/                                     │
    └─ 依赖: 所有模块                         │
                                              │
Day 7 ───────────────────────────────────────┘
└─ 联调集成
```

---

## 2. Day 1: Planner + ORM

### 2.1 core/planner.py

**目标**: 将自然语言任务拆解为结构化的子任务依赖图

**实现步骤**:

1. **定义数据类** (PlanNode, PlanGraph)
   - PlanNode: id, description, dependencies, estimated_duration, assigned_role, status
   - PlanGraph: nodes字典, root_node_id, 拓扑排序方法, 循环检测方法

2. **实现 Planner 类**
   - __init__(llm_router): 初始化 LLM 路由器
   - plan(task_description): 主入口，返回 PlanGraph
   - _build_prompt(task): 构建规划提示模板
   - _parse_plan_response(content): 3层解析策略
     - 策略1: 严格 JSON (json.loads)
     - 策略2: 宽松 JSON (正则提取 + 容错)
     - 策略3: 自然语言回退 (单任务模式)
   - _validate_dag(graph): 验证无环

3. **错误处理**
   - LLM调用失败: 抛出 LLMException
   - 解析失败: 回退到单任务模式
   - 循环依赖: 抛出 ValidationException

**代码结构**:

```python
class PlanNode:
    id: str
    description: str
    dependencies: List[str]
    estimated_duration: Optional[int]
    assigned_role: Optional[AgentRole]
    status: TaskStatus

class PlanGraph:
    nodes: Dict[str, PlanNode]
    root_node_id: str
    
    def get_execution_order(self) -> List[List[str]]: ...
    def validate_no_cycles(self) -> bool: ...
    def get_node(self, node_id: str) -> Optional[PlanNode]: ...

class Planner:
    def __init__(self, llm_router: LLMRouter): ...
    async def plan(self, task_description: str) -> PlanGraph: ...
    def _build_prompt(self, task: str) -> str: ...
    def _parse_plan_response(self, content: str) -> PlanGraph: ...
    def _parse_strict_json(self, content: str) -> Optional[PlanGraph]: ...
    def _parse_loose_json(self, content: str) -> Optional[PlanGraph]: ...
    def _fallback_single_task(self, task: str) -> PlanGraph: ...
    def _validate_dag(self, graph: PlanGraph) -> None: ...
```

**测试要点**:
- test_plan_strict_json: 严格JSON格式解析
- test_plan_loose_json: 宽松JSON格式解析（容错）
- test_plan_fallback: 解析失败回退到单任务
- test_plan_circular_dependency: 循环依赖检测
- test_get_execution_order: 拓扑排序正确性
- test_empty_task: 空任务处理

**时间估算**: 4-6 小时

---

### 2.2 database/models.py

**目标**: ORM 模型定义，支持任务、步骤、Agent状态的持久化

**实现步骤**:

1. **导入和基础**
   - from datetime import datetime, timezone
   - from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Integer
   - from sqlalchemy.orm import relationship
   - from database.connection import Base

2. **定义 TaskORM**
   - id (String, PK)
   - title (String, not null)
   - description (String, not null)
   - status (String, default="pending")
   - created_at (DateTime, default=lambda: datetime.now(timezone.utc))
   - updated_at (DateTime, nullable)
   - parent_id (String, FK→tasks.id, nullable)
   - metadata (JSON, default=dict)
   - steps relationship

3. **定义 StepORM**
   - id (String, PK)
   - task_id (String, FK→tasks.id, not null)
   - agent_id (String, not null)
   - agent_role (String, not null)
   - step_number (Integer, not null)
   - step_type (String, not null)
   - content (String, not null)
   - timestamp (DateTime, default=lambda: datetime.now(timezone.utc))
   - task relationship

4. **定义 AgentStateORM**
   - id (String, PK)
   - role (String, not null)
   - name (String, not null)
   - status (String, default="idle")
   - current_task_id (String, FK→tasks.id, nullable)
   - created_at (DateTime, default=lambda: datetime.now(timezone.utc))
   - updated_at (DateTime, nullable)

5. **初始化函数**
   - init_db(): 创建所有表

**代码结构**:

```python
class TaskORM(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True)
    # ... 其他字段
    steps = relationship("StepORM", back_populates="task")

class StepORM(Base):
    __tablename__ = "steps"
    id = Column(String, primary_key=True)
    # ... 其他字段
    task = relationship("TaskORM", back_populates="steps")

class AgentStateORM(Base):
    __tablename__ = "agent_states"
    id = Column(String, primary_key=True)
    # ... 其他字段
```

**测试要点**:
- test_task_creation: 任务创建和字段验证
- test_step_creation: 步骤创建和外键关联
- test_agent_state_creation: Agent状态创建
- test_relationship: 关系查询（task.steps）
- test_datetime_timezone: 时区正确性

**时间估算**: 2-3 小时

**Day 1 总计**: 6-9 小时

---

## 3. Day 2: Agent 角色

### 3.1 agents/executor_agent.py

**目标**: 通用执行者，能调用所有工具

**实现步骤**:

1. **继承 BaseAgent**
   - class ExecutorAgent(BaseAgent)
   - role = AgentRole.EXECUTOR
   - name = "执行者"

2. **定义系统提示**
   - get_system_prompt(): 返回角色定义和工具使用说明

3. **定义可用工具**
   - tools 属性: 所有工具（web_search, calculator）

4. **实现 execute 方法**
   - 构建 ReAct 循环
   - 调用 LLM 获取思考/行动
   - 执行工具调用
   - 返回结果

**代码结构**:

```python
class ExecutorAgent(BaseAgent):
    role = AgentRole.EXECUTOR
    name = "执行者"
    description = "通用任务执行者，能调用所有工具"
    
    def get_system_prompt(self) -> str: ...
    
    @property
    def tools(self) -> List[BaseTool]: ...
    
    async def execute(self, task: Task, context: str = None) -> AsyncGenerator[AgentStep, None]: ...
```

**测试要点**:
- test_executor_creation: Agent创建
- test_executor_tools: 工具集验证
- test_executor_execute: 执行流程

**时间估算**: 2-3 小时

---

### 3.2 agents/researcher_agent.py

**目标**: 研究员，专注于信息收集

**实现步骤**:

1. **继承 BaseAgent**
   - class ResearcherAgent(BaseAgent)
   - role = AgentRole.RESEARCHER
   - name = "研究员"

2. **定义系统提示**
   - 强调信息收集和分析能力

3. **定义可用工具**
   - tools 属性: [WebSearchTool]

4. **实现 execute 方法**
   - 使用 ReAct 循环进行搜索
   - 分析和总结搜索结果
   - 返回结构化报告

**代码结构**:

```python
class ResearcherAgent(BaseAgent):
    role = AgentRole.RESEARCHER
    name = "研究员"
    description = "信息收集和分析专家"
    
    def get_system_prompt(self) -> str: ...
    
    @property
    def tools(self) -> List[BaseTool]: ...
    
    async def execute(self, task: Task, context: str = None) -> AsyncGenerator[AgentStep, None]: ...
```

**测试要点**:
- test_researcher_creation: Agent创建
- test_researcher_tools: 只有WebSearchTool
- test_researcher_search: 搜索执行流程

**时间估算**: 2-3 小时

---

### 3.3 agents/factory.py

**目标**: 根据角色创建对应的 Agent 实例

**实现步骤**:

1. **定义注册表**
   - _registry: Dict[AgentRole, Type[BaseAgent]]

2. **实现 create 方法**
   - 根据 role 查找对应的 Agent 类
   - 实例化并返回

3. **实现 register 方法**
   - 支持动态注册新 Agent 类型（插件扩展）

4. **错误处理**
   - 未知角色: 抛出 ValueError

**代码结构**:

```python
class AgentFactory:
    _registry: Dict[AgentRole, Type[BaseAgent]] = {
        AgentRole.EXECUTOR: ExecutorAgent,
        AgentRole.RESEARCHER: ResearcherAgent,
        # Week 3 添加更多
    }
    
    @classmethod
    def create(cls, role: AgentRole, llm_router: LLMRouter) -> BaseAgent: ...
    
    @classmethod
    def register(cls, role: AgentRole, agent_class: Type[BaseAgent]) -> None: ...
    
    @classmethod
    def get_available_roles(cls) -> List[AgentRole]: ...
```

**测试要点**:
- test_factory_create_executor: 创建Executor
- test_factory_create_researcher: 创建Researcher
- test_factory_unknown_role: 未知角色抛出异常
- test_factory_register: 动态注册

**时间估算**: 1-2 小时

**Day 2 总计**: 5-8 小时

---

## 4. Day 3: A2A Bus + 工具

### 4.1 core/a2a_bus.py

**目标**: Agent 间异步消息总线

**实现步骤**:

1. **定义 A2AMessage 数据类**
   - id, sender_id, receiver_id, message_type, content, correlation_id, timestamp

2. **实现 A2ABus 类**
   - __init__: 初始化队列字典和历史列表
   - register(agent_id): 为Agent创建队列
   - unregister(agent_id): 清理Agent资源
   - send(message): 点对点发送
   - broadcast(message): 广播（排除发送者）
   - request_response(request, timeout): 请求-响应模式
   - receive(agent_id): 阻塞接收
   - get_history(agent_id): 获取历史消息

3. **历史管理**
   - _add_to_history: 添加消息，自动清理（保留1000条）

**代码结构**:

```python
@dataclass
class A2AMessage:
    id: str
    sender_id: str
    receiver_id: Optional[str]
    message_type: str
    content: str
    correlation_id: Optional[str]
    timestamp: datetime

class A2ABus:
    def __init__(self): ...
    async def register(self, agent_id: str) -> None: ...
    async def unregister(self, agent_id: str) -> None: ...
    async def send(self, message: A2AMessage) -> None: ...
    async def broadcast(self, message: A2AMessage) -> None: ...
    async def request_response(self, request: A2AMessage, timeout: float = 30.0) -> Optional[A2AMessage]: ...
    async def receive(self, agent_id: str) -> A2AMessage: ...
    def get_history(self, agent_id: Optional[str] = None) -> List[A2AMessage]: ...
    def _add_to_history(self, message: A2AMessage) -> None: ...
```

**测试要点**:
- test_send_receive: 点对点发送和接收
- test_broadcast: 广播消息
- test_request_response: 请求-响应模式
- test_request_response_timeout: 请求超时
- test_history_cleanup: 历史自动清理
- test_unregister: 注销Agent

**时间估算**: 3-4 小时

---

### 4.2 tools/web_search.py

**目标**: Mock 搜索工具

**实现步骤**:

1. **继承 BaseTool**（Week 1 已定义）
   - class WebSearchTool(BaseTool)

2. **定义元数据**
   - name = "web_search"
   - description = "搜索互联网信息"

3. **实现 execute 方法**
   - 根据 query 返回预设结果
   - 支持常见查询的固定回答
   - 未知查询返回通用模板

**代码结构**:

```python
class WebSearchTool(BaseTool):
    name = "web_search"
    description = "搜索互联网信息"
    
    # 预设搜索结果
    _mock_results: Dict[str, str] = {
        "python asyncio": "asyncio 是 Python 的异步 I/O 库...",
        "default": "搜索: {query}"
    }
    
    async def execute(self, query: str) -> str: ...
    
    def get_schema(self) -> Dict[str, Any]: ...
```

**测试要点**:
- test_web_search_known_query: 已知查询返回预设结果
- test_web_search_unknown_query: 未知查询返回模板
- test_web_search_schema: 工具schema正确

**时间估算**: 1 小时

---

### 4.3 tools/calculator.py

**目标**: 安全数学计算工具

**实现步骤**:

1. **继承 BaseTool**
   - class CalculatorTool(BaseTool)

2. **定义元数据**
   - name = "calculator"
   - description = "安全数学计算器"

3. **实现 execute 方法**
   - 解析数学表达式
   - 使用安全计算方式（避免 eval）
   - 支持基本运算: +, -, *, /, **
   - 返回计算结果或错误信息

4. **安全考虑**
   - 禁止执行任意代码
   - 只支持纯数学表达式
   - 处理除零错误

**代码结构**:

```python
class CalculatorTool(BaseTool):
    name = "calculator"
    description = "安全数学计算器"
    
    async def execute(self, expression: str) -> str: ...
    
    def _safe_evaluate(self, expression: str) -> float: ...
    
    def get_schema(self) -> Dict[str, Any]: ...
```

**测试要点**:
- test_calculator_addition: 加法
- test_calculator_division: 除法
- test_calculator_division_by_zero: 除零错误
- test_calculator_complex: 复杂表达式
- test_calculator_invalid: 非法输入

**时间估算**: 1-2 小时

**Day 3 总计**: 5-7 小时

---

## 5. Day 4: 前端骨架

### 5.1 安装依赖

**命令**:
```bash
cd frontend
npm install tailwindcss postcss autoprefixer react-router-dom zustand axios
npx tailwindcss init -p
```

**配置**:
- tailwind.config.js: content 路径配置
- postcss.config.js: 自动配置
- index.css: 导入 Tailwind 指令

**时间估算**: 30 分钟

---

### 5.2 组件实现

**src/components/layout/Sidebar.tsx**:
- 左侧导航栏
- 链接: Dashboard, Tasks, Agents
- 响应式（移动端可折叠）

**src/components/layout/Header.tsx**:
- 顶部栏
- 标题和用户信息占位
- 移动端菜单按钮

**src/components/layout/Layout.tsx**:
- 布局容器
- Sidebar + Header + Content
- 使用 flex 布局

**时间估算**: 2-3 小时

---

### 5.3 页面实现

**src/pages/Dashboard.tsx**:
- 欢迎信息
- 任务统计卡片（总数、进行中、已完成）
- Agent 状态列表
- 快速操作按钮（创建任务）

**src/pages/Tasks.tsx**:
- 任务列表表格
- 状态标签
- 创建任务按钮
- 点击跳转详情

**src/pages/TaskDetail.tsx**:
- 任务基本信息
- 执行步骤列表
- 步骤类型标签（thought, action, observation, final）
- 实时更新（预留 SSE 接口）

**时间估算**: 3-4 小时

---

### 5.4 Store 实现

**src/stores/taskStore.ts**:
```typescript
interface TaskStore {
  tasks: Task[];
  currentTask: Task | null;
  steps: AgentStep[];
  isLoading: boolean;
  error: string | null;
  
  fetchTasks: () => Promise<void>;
  createTask: (description: string) => Promise<void>;
  fetchTaskDetail: (id: string) => Promise<void>;
  subscribeToTask: (id: string) => void;
  clearError: () => void;
}
```

**src/stores/agentStore.ts**:
```typescript
interface AgentStore {
  agents: AgentState[];
  isLoading: boolean;
  error: string | null;
  
  fetchAgents: () => Promise<void>;
  subscribeToAgents: () => void;
  clearError: () => void;
}
```

**时间估算**: 2 小时

---

### 5.5 路由和 API

**src/App.tsx**:
- BrowserRouter 配置
- Routes: /, /tasks, /tasks/:id
- Layout 包裹

**src/api/client.ts**:
- Axios 实例配置
- 基础 URL: http://localhost:8000/api/v1
- 请求/响应拦截器
- SSE 连接封装

**时间估算**: 1-2 小时

**Day 4 总计**: 8-11 小时

---

## 6. Day 5: Orchestrator

### 6.1 core/orchestrator.py

**目标**: 按依赖图调度 Agent 执行

**实现步骤**:

1. **定义 Orchestrator 类**
   - __init__(llm_router, tool_registry, max_concurrency=3)
   - semaphore: asyncio.Semaphore 控制并发
   - agents: Dict[AgentRole, BaseAgent] 缓存Agent实例

2. **实现 execute_plan 方法**
   - 输入: PlanGraph, CancellationToken
   - 输出: AsyncGenerator[AgentStep, None]
   - 流程:
     1. 获取分层执行顺序 (plan.get_execution_order())
     2. 逐层执行:
        - 同层节点并行执行 (asyncio.gather)
        - 使用信号量控制并发数
     3. 每个节点:
        - 检查取消状态
        - 调用 _execute_node
        - 生成 AgentStep 事件
     4. 层间等待上一层完成

3. **实现 _execute_node 方法**
   - 根据节点 role 获取/创建 Agent
   - 构建 Task 对象
   - 调用 Agent.execute()
   - 设置超时 (默认120s)
   - 返回 TaskResult

4. **实现 _get_or_create_agent 方法**
   - 检查缓存中是否已有该角色Agent
   - 没有则通过 AgentFactory 创建
   - 返回 Agent 实例

5. **超时处理**
   - 使用 asyncio.wait_for 包装执行
   - 超时后取消任务并清理

**代码结构**:

```python
class Orchestrator:
    def __init__(self, llm_router: LLMRouter, tool_registry: ToolRegistry, max_concurrency: int = 3): ...
    
    async def execute_plan(self, plan: PlanGraph, cancellation_token: Optional[CancellationToken] = None) -> AsyncGenerator[AgentStep, None]: ...
    
    async def _execute_node(self, node: PlanNode, cancellation_token: Optional[CancellationToken]) -> TaskResult: ...
    
    def _get_or_create_agent(self, role: AgentRole) -> BaseAgent: ...
    
    async def _execute_layer(self, layer: List[str], plan: PlanGraph, cancellation_token: Optional[CancellationToken]) -> List[TaskResult]: ...
```

**测试要点**:
- test_execute_single_node: 单节点执行
- test_execute_parallel: 并行执行（同层多个节点）
- test_execute_sequential: 顺序执行（层间依赖）
- test_execute_cancellation: 取消执行
- test_execute_timeout: 超时处理
- test_concurrency_limit: 并发数限制（信号量）
- test_agent_reuse: Agent 实例复用

**时间估算**: 6-8 小时

**Day 5 总计**: 6-8 小时

---

## 7. Day 6: API 路由 + 测试

### 7.1 api/routes/tasks.py

**目标**: 任务 CRUD + SSE 实时流

**实现步骤**:

1. **定义 Pydantic 模型**
   - CreateTaskRequest: title, description
   - TaskResponse: id, title, description, status, created_at, updated_at
   - StepResponse: id, task_id, agent_id, agent_role, step_type, content, timestamp
   - TaskDetailResponse: TaskResponse + steps

2. **实现端点**
   - POST /: 创建任务
     - 保存到数据库
     - 调用 Planner 拆解
     - 启动 Orchestrator 执行（后台任务）
     - 返回任务信息
   - GET /: 获取任务列表
   - GET /{task_id}: 获取任务详情（含步骤）
   - DELETE /{task_id}: 取消任务
   - GET /{task_id}/stream: SSE 实时流
     - 订阅 Orchestrator 的事件生成器
     - 格式化 SSE 事件
     - 处理连接关闭

3. **错误处理**
   - 任务不存在: 404
   - 创建失败: 500
   - SSE 连接断开: 优雅处理

**代码结构**:

```python
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

class CreateTaskRequest(BaseModel): ...
class TaskResponse(BaseModel): ...
class StepResponse(BaseModel): ...
class TaskDetailResponse(TaskResponse): ...

@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest): ...

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(): ...

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str): ...

@router.delete("/{task_id}")
async def cancel_task(task_id: str): ...

@router.get("/{task_id}/stream")
async def stream_task(task_id: str): ...
```

**测试要点**:
- test_create_task: 创建任务成功
- test_create_task_validation: 参数验证失败
- test_list_tasks: 获取列表
- test_get_task: 获取详情
- test_get_task_not_found: 任务不存在
- test_cancel_task: 取消任务
- test_stream_task: SSE 流

**时间估算**: 4-5 小时

---

### 7.2 api/routes/agents.py

**目标**: Agent 查询 + 消息发送 + SSE 状态流

**实现步骤**:

1. **定义 Pydantic 模型**
   - MessageRequest: content, message_type
   - AgentResponse: id, role, name, status, current_task_id, created_at
   - AgentMessageResponse: id, sender_id, receiver_id, message_type, content, timestamp

2. **实现端点**
   - GET /: 获取Agent列表
   - GET /{agent_id}: 获取Agent详情
   - POST /{agent_id}/message: 发送消息
   - GET /stream: SSE Agent状态流

**代码结构**:

```python
router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

class MessageRequest(BaseModel): ...
class AgentResponse(BaseModel): ...
class AgentMessageResponse(BaseModel): ...

@router.get("/", response_model=List[AgentResponse])
async def list_agents(): ...

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str): ...

@router.post("/{agent_id}/message", response_model=AgentMessageResponse)
async def send_message(agent_id: str, request: MessageRequest): ...

@router.get("/stream")
async def stream_agents(): ...
```

**测试要点**:
- test_list_agents: 获取列表
- test_get_agent: 获取详情
- test_send_message: 发送消息
- test_stream_agents: SSE 流

**时间估算**: 2-3 小时

---

### 7.3 测试实现

**tests/unit/test_planner.py**:
- test_plan_strict_json
- test_plan_loose_json
- test_plan_fallback
- test_plan_circular_dependency
- test_get_execution_order

**tests/unit/test_orchestrator.py**:
- test_execute_single_node
- test_execute_parallel
- test_execute_sequential
- test_execute_cancellation
- test_execute_timeout
- test_concurrency_limit

**tests/unit/test_a2a_bus.py**:
- test_send_receive
- test_broadcast
- test_request_response
- test_request_response_timeout
- test_history_cleanup

**tests/unit/test_agents.py**:
- test_executor_creation
- test_researcher_creation
- test_executor_execute
- test_researcher_search

**tests/integration/test_task_flow.py**:
- test_end_to_end_task: 创建 → 规划 → 执行 → 完成
- test_multi_agent_collaboration: Researcher → Executor
- test_cancel_flow: 创建 → 取消 → 清理

**时间估算**: 4-6 小时

**Day 6 总计**: 10-14 小时

---

## 8. Day 7: 联调

### 8.1 活动清单

**上午**:
- [ ] 启动后端服务（uvicorn）
- [ ] 启动前端服务（npm run dev）
- [ ] 测试任务创建流程
- [ ] 测试 SSE 实时流
- [ ] 检查数据库持久化

**下午**:
- [ ] 运行完整测试套件
- [ ] 修复发现的 Bug
- [ ] 性能调优（如有必要）
- [ ] 代码格式化（black + isort）
- [ ] 类型检查（mypy）

**傍晚**:
- [ ] 准备演示脚本
- [ ] 更新文档
- [ ] 验收清单确认

### 8.2 演示脚本

**场景**: 用户研究 Python asyncio

```
1. 打开前端 Dashboard 页面
2. 点击"创建任务"
3. 输入: "研究 Python asyncio 最佳实践"
4. 点击提交
5. 观察:
   - 任务状态: pending → planning → executing → completed
   - Planner 拆解为子任务
   - Researcher 执行搜索
   - Executor 汇总结果
6. 查看任务详情页面:
   - 执行步骤列表
   - 每个步骤的 thought/action/observation
7. 验证数据库:
   - 任务已保存
   - 步骤已记录
```

**Day 7 总计**: 6-8 小时

---

## 9. 并行执行建议

### 9.1 可并行的任务

**Day 1-2 期间**:
- Planner (Day 1) 和 ORM 模型 (Day 1) 可并行
- Agent 角色 (Day 2) 可并行开发
  - ExecutorAgent 和 ResearcherAgent 互不依赖

**Day 3-4 期间**:
- A2A Bus (Day 3) 和 工具 (Day 3) 可并行
- 前端 (Day 4) 与后端完全独立，可并行

**Day 5-6 期间**:
- Orchestrator (Day 5) 和 API 路由 (Day 6) 部分并行
  - 先完成 Orchestrator 核心逻辑
  - 再并行开发 API 路由和测试

### 9.2 并行执行方案

如果有多人协作，建议分组：

**组 A（后端核心）**:
- Day 1: Planner
- Day 2: Orchestrator
- Day 3: API 路由

**组 B（Agent + 工具）**:
- Day 1: ORM 模型
- Day 2: Agent 角色 + Factory
- Day 3: A2A Bus + 工具

**组 C（前端）**:
- Day 1-2: 环境配置 + 组件库
- Day 3-4: 页面 + Stores
- Day 5: API 对接

---

## 10. 风险缓解

### 10.1 风险登记册

| 风险 | 可能性 | 影响 | 缓解措施 | 责任人 |
|------|--------|------|---------|--------|
| LLM 规划不稳定 | 高 | 中 | 3种解析策略 + 单任务fallback | Day 1 |
| 并发执行死锁 | 中 | 高 | Semaphore + 超时 + 充分测试 | Day 5 |
| SSE 连接泄漏 | 低 | 中 | 心跳检测 + 连接清理 | Day 6 |
| 前端状态不一致 | 中 | 中 | Zustand + 类型完整 + 测试 | Day 4 |
| 数据库迁移问题 | 低 | 高 | Alembic + 版本控制 | Day 1 |

### 10.2 应急预案

**如果 Day 1 Planner 无法按时完成**:
- 简化: 先实现单任务模式（无依赖图）
- 后续: Day 5 补充完整 Planner

**如果 Day 5 Orchestrator 并发问题复杂**:
- 简化: 先实现串行执行
- 后续: Week 3 补充并行执行

**如果前端进度滞后**:
- 最小化: 只保留 Dashboard + Task 列表
- Mock: 使用静态数据代替真实 API

---

## 附录 A: 文件清单

### Day 1
- [ ] `core/planner.py` (200-300 行)
- [ ] `database/models.py` (100-150 行)

### Day 2
- [ ] `agents/executor_agent.py` (100-150 行)
- [ ] `agents/researcher_agent.py` (100-150 行)
- [ ] `agents/factory.py` (50-80 行)

### Day 3
- [ ] `core/a2a_bus.py` (150-200 行)
- [ ] `tools/web_search.py` (50-80 行)
- [ ] `tools/calculator.py` (80-120 行)

### Day 4
- [ ] `frontend/package.json` (更新)
- [ ] `frontend/tailwind.config.js` (新建)
- [ ] `frontend/src/components/layout/Sidebar.tsx` (100-150 行)
- [ ] `frontend/src/components/layout/Header.tsx` (80-120 行)
- [ ] `frontend/src/components/layout/Layout.tsx` (50-80 行)
- [ ] `frontend/src/pages/Dashboard.tsx` (150-200 行)
- [ ] `frontend/src/pages/Tasks.tsx` (150-200 行)
- [ ] `frontend/src/pages/TaskDetail.tsx` (200-250 行)
- [ ] `frontend/src/stores/taskStore.ts` (100-150 行)
- [ ] `frontend/src/stores/agentStore.ts` (80-120 行)
- [ ] `frontend/src/api/client.ts` (80-120 行)
- [ ] `frontend/src/App.tsx` (更新, 50-80 行)

### Day 5
- [ ] `core/orchestrator.py` (250-350 行)

### Day 6
- [ ] `api/routes/tasks.py` (200-300 行)
- [ ] `api/routes/agents.py` (150-200 行)
- [ ] `tests/unit/test_planner.py` (150-200 行)
- [ ] `tests/unit/test_orchestrator.py` (200-250 行)
- [ ] `tests/unit/test_a2a_bus.py` (150-200 行)
- [ ] `tests/unit/test_agents.py` (100-150 行)
- [ ] `tests/integration/test_task_flow.py` (200-300 行)

### Day 7
- [ ] 联调修复

**总计**: ~25 个新文件，~4000-5000 行代码

---

## 附录 B: 依赖检查清单

### 后端依赖（requirements.txt 已有）
- [x] fastapi
- [x] uvicorn
- [x] pydantic
- [x] sqlalchemy
- [x] pytest
- [x] pytest-asyncio

### 前端依赖（需安装）
- [ ] tailwindcss
- [ ] postcss
- [ ] autoprefixer
- [ ] react-router-dom
- [ ] zustand
- [ ] axios

### 外部服务
- [x] LLM API (Kimi/DeepSeek) - 配置在 .env
- [ ] Redis - 可选，Week 3 使用
- [ ] PostgreSQL - 可选，生产环境使用

---

> **实施计划结束**
> 
> 下一步：开始按 Day 1 → Day 7 顺序编码实现，或按并行建议分组执行
