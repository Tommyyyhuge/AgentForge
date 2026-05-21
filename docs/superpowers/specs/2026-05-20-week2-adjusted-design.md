# Week 2 调整设计文档：多 Agent 调度 + 前端骨架（务实版）

> **版本**: 1.1（调整后）
> **日期**: 2026-05-20
> **基于**: Week 1 完成的基础设施 + Week 2 原始设计
> **核心原则**: **Week 2 的目标不是"完成所有功能"，而是"让第一个端到端流程跑起来"**
>   （用户提交任务 → Planner 拆解 → Agent 执行 → 返回结果）

---

## 目录

1. [调整概述](#1-调整概述)
2. [风险分析](#2-风险分析)
3. [调整后的执行计划](#3-调整后的执行计划)
4. [模块详细设计](#4-模块详细设计)
5. [数据库设计](#5-数据库设计)
6. [API 设计](#6-api-设计)
7. [前端设计](#7-前端设计)
8. [测试策略](#8-测试策略)
9. [验收标准](#9-验收标准)
10. [与 Week 3 的衔接](#10-与-week-3-的衔接)

---

## 1. 调整概述

### 1.1 原始设计的问题

原始 Week 2 设计试图在 7 天内完成：
- 后端：Planner + Orchestrator + A2A Bus + 6 个 Agent + API 路由
- 前端：完整骨架 + 所有页面 + Stores

**问题**：过于理想化，没有考虑依赖关系和实际开发工作量。

### 1.2 调整原则

1. **端到端优先**：先让一个简单的流程跑通，再逐步完善
2. **依赖驱动**：后置模块等前置就绪后再写，避免返工
3. **MVP 思维**：Week 2 只做展示协作流程所需的最小功能集
4. **可演示**：Day 7 结束时，能演示"创建任务 → 自动拆解 → Agent 执行 → 看到结果"

---

## 2. 风险分析

### 2.1 已解决的风险

| 风险 | 原始设计 | 调整后 | 状态 |
|------|---------|--------|------|
| Day 1 太赶 | Planner + Orchestrator | **只写 Planner** | ✅ 解决 |
| 6 个 Agent 一天写完 | 全部 Day 2 | **只做 2-3 个** | ✅ 解决 |
| API 过早 | Day 3 | **Day 6** | ✅ 解决 |
| 无数据库 | 未提及 | **Day 1 补 ORM** | ✅ 解决 |
| 无工具 | 未提及 | **Day 3 做 Mock 工具** | ✅ 解决 |

### 2.2 剩余风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| LLM 规划不稳定 | 高 | 中 | 3 种解析策略 + 单任务 fallback |
| 并发执行复杂 | 中 | 高 | Semaphore(3) + 充分测试 |
| 前端状态管理 | 中 | 中 | Zustand 简化 + 类型完整 |
| SSE 连接管理 | 低 | 中 | 心跳检测 + 自动重连 |

---

## 3. 调整后的执行计划

### Day 1: Planner + ORM 模型

**目标**：让任务能被拆解为结构化依赖图

**产出文件**：
- `core/planner.py` - 任务规划器
- `database/models.py` - ORM 模型

**依赖**：Week 1 的 `llm_client.py`, `models/schemas.py`

**验收标准**：
- [ ] Planner 能解析严格 JSON 格式
- [ ] Planner 能解析宽松 JSON 格式
- [ ] Planner 解析失败时回退到单任务模式
- [ ] ORM 模型包含 Task, AgentState, Step

---

### Day 2: 核心 Agent（2-3 个）

**目标**：让 Agent 能实际执行任务

**产出文件**：
- `agents/executor_agent.py` - 通用执行者（最重要，能调用所有工具）
- `agents/researcher_agent.py` - 研究员（有 WebSearch 工具）
- `agents/factory.py` - Agent 工厂

**暂不实现**（Week 3）：
- PlannerAgent, CoderAgent, WriterAgent, ReviewerAgent

**依赖**：Day 1 的 Planner, Week 1 的 `agents/base.py`

**验收标准**：
- [ ] ExecutorAgent 能独立创建和执行
- [ ] ResearcherAgent 能独立创建和执行
- [ ] AgentFactory 能创建所有已实现角色

---

### Day 3: A2A Bus + Mock 工具

**目标**：让 Agent 能通信，ReAct 循环能实际调用工具

**产出文件**：
- `core/a2a_bus.py` - Agent 间消息总线
- `tools/web_search.py` - Mock 版本（返回固定搜索结果）
- `tools/calculator.py` - 真实实现（安全数学计算）

**暂不实现**（Week 3）：
- CodeExecuteTool, FileIOTool, MemorySearchTool 等

**依赖**：Day 2 的 Agent

**验收标准**：
- [ ] A2A 点对点消息可达
- [ ] A2A 广播消息可达
- [ ] WebSearch Mock 工具返回固定结果
- [ ] Calculator 工具能安全计算数学表达式

---

### Day 4: 前端骨架

**目标**：有可运行的 Web 界面

**产出文件**：
- `package.json`（更新依赖：Tailwind, Router, Zustand, Axios）
- `src/components/layout/Sidebar.tsx`
- `src/components/layout/Header.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/Tasks.tsx`
- `src/pages/TaskDetail.tsx`
- `src/App.tsx`（路由配置）

**暂不实现**（Week 3）：
- AgentMonitor, MultiAgentChat, Settings 页面
- 真实 API 对接（先用 Mock 数据）

**验收标准**：
- [ ] `npm run dev` 正常启动
- [ ] 路由正常工作（/ → Dashboard, /tasks → Tasks）
- [ ] Tailwind 样式生效
- [ ] 页面布局完整（Sidebar + Header + Content）

---

### Day 5: Orchestrator

**目标**：让多个 Agent 能按依赖图协作执行

**产出文件**：
- `core/orchestrator.py` - 任务调度器

**为什么放在 Day 5？**
- Orchestrator 依赖 Planner（Day 1）
- Orchestrator 依赖 Agent（Day 2）
- Orchestrator 依赖 A2A Bus（Day 3）
- 等所有前置就绪后再写，避免接口不匹配返工

**验收标准**：
- [ ] 能并行执行无依赖任务（Semaphore 控制并发数 ≤3）
- [ ] 能按序执行有依赖任务
- [ ] 超时后优雅退出并清理资源
- [ ] 取消后停止所有子任务

---

### Day 6: API 路由 + 测试

**目标**：前后端能通信，核心逻辑有测试保护

**产出文件**：
- `api/routes/tasks.py` - 任务 CRUD + SSE 实时流
- `api/routes/agents.py` - Agent 查询 + 状态流
- `tests/unit/test_planner.py`
- `tests/unit/test_orchestrator.py`
- `tests/unit/test_agents.py`
- `tests/integration/test_task_flow.py`

**为什么 API 放在 Day 6？**
- Day 6 时 Orchestrator 已就绪，API 有东西可暴露
- 避免 Day 3 写 API 时只能暴露空接口

**验收标准**：
- [ ] POST /api/v1/tasks 能创建任务
- [ ] GET /api/v1/tasks/{id}/stream 返回 SSE 流
- [ ] 单元测试覆盖率 > 60%
- [ ] 集成测试：创建任务 → 执行 → 完成

---

### Day 7: 联调 + Bug 修复

**目标**：Day 7 结束时能演示完整流程

**活动**：
- 前后端联调
- 端到端测试
- Bug 修复
- 性能调优
- 文档更新

**演示脚本**：
1. 打开前端页面
2. 点击"创建任务"
3. 输入："研究 Python asyncio 最佳实践"
4. 看到 Planner 拆解为子任务
5. 看到 Researcher Agent 执行搜索
6. 看到 Executor Agent 汇总结果
7. 任务状态变为"已完成"

---

## 4. 模块详细设计

### 4.1 Planner（Day 1）

**文件**: `core/planner.py`

**核心类**:

```python
class PlanNode:
    """计划节点"""
    id: str                          # 节点ID（如 "step-1"）
    description: str                 # 子任务描述
    dependencies: List[str]          # 依赖的其他节点ID
    estimated_duration: Optional[int] # 预估执行时间（秒）
    assigned_role: Optional[AgentRole] # 分配的Agent角色
    status: TaskStatus               # 当前状态

class PlanGraph:
    """计划依赖图（DAG）"""
    nodes: Dict[str, PlanNode]       # 所有节点
    root_node_id: str                # 根节点ID
    
    def get_execution_order(self) -> List[List[str]]:
        """拓扑排序，返回分层执行顺序
        
        返回：[["step-1", "step-2"], ["step-3"], ["step-4", "step-5"]]
        每一层内的节点可以并行执行
        """
        
    def validate_no_cycles(self) -> bool:
        """检测循环依赖，如果有循环则抛出异常"""

class Planner:
    """任务规划器"""
    
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
    
    async def plan(self, task_description: str) -> PlanGraph:
        """将自然语言任务拆解为依赖图"""
        # 1. 构建规划提示
        # 2. 调用 LLM
        # 3. 解析响应（3 种策略）
        # 4. 构建依赖图
        # 5. 验证无循环
        # 6. 返回 PlanGraph
    
    def _parse_plan_response(self, content: str) -> PlanGraph:
        """解析 LLM 响应（3 层回退）"""
        # 策略 1: 严格 JSON（try/except）
        # 策略 2: 宽松 JSON（正则提取 + 容错）
        # 策略 3: 自然语言回退（单任务模式）
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

### 4.2 Orchestrator（Day 5）

**文件**: `core/orchestrator.py`

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
        """执行计划图
        
        流程:
        1. 拓扑排序，获取分层执行顺序
        2. 逐层执行（同层并行）
        3. 使用信号量控制并发（最多3个）
        4. 每个子任务设置超时（默认120s）
        5. 检查取消状态
        6. 聚合结果，生成 AgentStep 事件
        """
    
    async def _execute_node(
        self,
        node: PlanNode,
        cancellation_token: Optional[CancellationToken]
    ) -> TaskResult:
        """执行单个节点
        
        流程:
        1. 根据角色获取/创建 Agent
        2. 构建 Task 对象
        3. 调用 Agent.execute()
        4. 设置超时
        5. 返回结果
        """
    
    def _get_or_create_agent(self, role: AgentRole) -> BaseAgent:
        """获取或创建 Agent 实例（复用已有实例）"""
```

**执行流程示例**:

```
PlanGraph
├── Layer 1: [Node A, Node B]      -> 并行执行（最多3个）
├── Layer 2: [Node C]              -> 等待 A, B 完成
├── Layer 3: [Node D, Node E]      -> 等待 C 完成，D 和 E 并行
└── Layer 4: [Node F]              -> 等待 D, E 完成
```

**超时策略**:
- 任务级超时：单个节点执行超时（默认 120 秒）
- 计划级超时：整个计划执行超时（默认 600 秒）

---

### 4.3 A2A Bus（Day 3）

**文件**: `core/a2a_bus.py`

**核心类**:

```python
class A2AMessage:
    """A2A 消息"""
    id: str
    sender_id: str
    receiver_id: Optional[str]      # None 表示广播
    message_type: str               # "request", "response", "broadcast"
    content: str
    correlation_id: Optional[str]   # 请求-响应配对ID
    timestamp: datetime

class A2ABus:
    """A2A 消息总线"""
    
    def __init__(self):
        self._queues: Dict[str, asyncio.Queue] = {}
        self._history: List[A2AMessage] = []
        self._max_history = 1000
    
    async def register(self, agent_id: str):
        """注册 Agent 到总线"""
    
    async def unregister(self, agent_id: str):
        """从总线注销 Agent"""
    
    async def send(self, message: A2AMessage):
        """发送点对点消息"""
    
    async def broadcast(self, message: A2AMessage):
        """广播消息给所有 Agent（除了发送者）"""
    
    async def request_response(
        self,
        request: A2AMessage,
        timeout: float = 30.0
    ) -> Optional[A2AMessage]:
        """请求-响应模式（带超时）"""
    
    async def receive(self, agent_id: str) -> A2AMessage:
        """接收消息（阻塞）"""
    
    def get_history(self, agent_id: Optional[str] = None) -> List[A2AMessage]:
        """获取历史消息（可按 Agent 过滤）"""
```

---

### 4.4 Agent 角色（Day 2）

**设计原则**:
- 每个 Agent 继承 `BaseAgent`（Week 1 已实现）
- 通过 `get_system_prompt()` 定义角色行为
- 通过 `tools` 属性定义可用工具
- 通过 `role` 类属性标识角色

**Week 2 只实现 3 个角色**:

| Agent | 职责 | 特色工具 | 复杂度 |
|-------|------|---------|--------|
| **ExecutorAgent** | 通用执行 | 所有工具 | 高 |
| **ResearcherAgent** | 信息收集 | WebSearchTool | 中 |
| **PlannerAgent** | 任务规划 | - | 低 |

**暂不实现**（Week 3）:
- CoderAgent, WriterAgent, ReviewerAgent

**AgentFactory**:

```python
class AgentFactory:
    _registry: Dict[AgentRole, Type[BaseAgent]] = {
        AgentRole.PLANNER: PlannerAgent,
        AgentRole.RESEARCHER: ResearcherAgent,
        AgentRole.EXECUTOR: ExecutorAgent,
        # Week 3 再添加: Coder, Writer, Reviewer
    }
    
    @classmethod
    def create(cls, role: AgentRole, llm_router: LLMRouter) -> BaseAgent:
        agent_class = cls._registry[role]
        return agent_class(llm_router)
    
    @classmethod
    def register(cls, role: AgentRole, agent_class: Type[BaseAgent]):
        """注册新的 Agent 类型（插件扩展用）"""
        cls._registry[role] = agent_class
```

---

### 4.5 工具（Day 3）

**Week 2 只实现 2 个工具**:

| 工具 | 类型 | 说明 |
|------|------|------|
| **WebSearchTool** | Mock | 返回固定的搜索结果（让 ReAct 能跑起来） |
| **CalculatorTool** | 真实 | 安全的数学计算（eval 替代方案） |

**Mock 工具设计**:

```python
class WebSearchTool(BaseTool):
    """Web 搜索工具（Mock 版本）"""
    
    name = "web_search"
    description = "搜索互联网信息"
    
    async def execute(self, query: str) -> str:
        # Mock 实现：返回预设结果
        mock_results = {
            "python asyncio": "asyncio 是 Python 的异步 I/O 库...",
            "default": f"搜索结果：{query}"
        }
        return mock_results.get(query, mock_results["default"])
```

**工具注册流程**:

```python
# main.py 或工厂初始化代码
from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.tools.web_search import WebSearchTool
from agent_forge.tools.calculator import CalculatorTool

# 1. 创建工具注册表
tool_registry = ToolRegistry()

# 2. 注册工具实例
tool_registry.register(WebSearchTool())
tool_registry.register(CalculatorTool())

# 3. Agent 通过工厂创建时注入工具
from agent_forge.agents.factory import AgentFactory
from agent_forge.models.schemas import AgentRole

agent = AgentFactory.create(
    role=AgentRole.RESEARCHER,
    llm_router=llm_router,
    tool_registry=tool_registry  # 注入工具注册表
)

# 4. Agent 内部通过 tool_registry 获取工具
# class ResearcherAgent(BaseAgent):
#     async def execute(self, task):
#         web_search = self.tool_registry.get("web_search")
#         result = await web_search.execute("Python asyncio")
```

**工具生命周期管理**:
- **创建**: 在应用启动时（main.py）创建并注册
- **注入**: 通过 AgentFactory.create() 注入到 Agent
- **使用**: Agent 通过 `self.tool_registry.get(tool_name)` 获取工具实例
- **销毁**: 应用关闭时随 Agent 一起释放（无状态工具无需特殊清理）

**暂不实现**（Week 3）:
- CodeExecuteTool, FileIOTool, MemorySearchTool, AgentMessageTool, SummarizeTool

---

## 5. 数据库设计

### 5.1 ORM 模型（Day 1）

**文件**: `database/models.py`

```python
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Integer
from sqlalchemy.orm import relationship
from database.connection import Base

class TaskORM(Base):
    """任务表"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, planning, executing, completed, failed, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)
    parent_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    metadata = Column(JSON, default=dict)
    
    steps = relationship("StepORM", back_populates="task")

class StepORM(Base):
    """执行步骤表"""
    __tablename__ = "steps"
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    agent_id = Column(String, nullable=False)
    agent_role = Column(String, nullable=False)
    step_number = Column(Integer, nullable=False)
    step_type = Column(String, nullable=False)  # thought, action, observation, final, error
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    task = relationship("TaskORM", back_populates="steps")

class AgentStateORM(Base):
    """Agent 状态表"""
    __tablename__ = "agent_states"
    
    id = Column(String, primary_key=True)
    role = Column(String, nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, default="idle")  # idle, busy, error
    current_task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)
```

---

## 6. API 设计

### 6.1 任务 API（Day 6）

**文件**: `api/routes/tasks.py`

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# 请求/响应模型
class CreateTaskRequest(BaseModel):
    title: str
    description: str

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class StepResponse(BaseModel):
    id: str
    task_id: str
    agent_id: str
    agent_role: str
    step_type: str
    content: str
    timestamp: datetime

class TaskDetailResponse(TaskResponse):
    steps: List[StepResponse]

# API 端点
@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建任务"""
    # 1. 保存任务到数据库
    # 2. 调用 Planner 拆解任务
    # 3. 调用 Orchestrator 执行
    # 4. 返回任务信息

@router.get("/", response_model=List[TaskResponse])
async def list_tasks():
    """获取任务列表"""

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """获取任务详情"""

@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""

@router.get("/{task_id}/stream")
async def stream_task(task_id: str):
    """SSE：任务执行实时流"""
    return StreamingResponse(
        event_generator(task_id),
        media_type="text/event-stream"
    )
```

### 6.2 Agent API（Day 6）

**文件**: `api/routes/agents.py`

```python
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# 请求/响应模型
class MessageRequest(BaseModel):
    content: str
    message_type: str = "request"

class AgentResponse(BaseModel):
    id: str
    role: str
    name: str
    status: str
    current_task_id: Optional[str] = None
    created_at: datetime

class AgentMessageResponse(BaseModel):
    id: str
    sender_id: str
    receiver_id: Optional[str]
    message_type: str
    content: str
    timestamp: datetime

# API 端点
@router.get("/", response_model=List[AgentResponse])
async def list_agents():
    """获取 Agent 列表"""

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """获取 Agent 详情"""

@router.post("/{agent_id}/message", response_model=AgentMessageResponse)
async def send_message(agent_id: str, request: MessageRequest):
    """发送消息给 Agent"""

@router.get("/stream")
async def stream_agents():
    """SSE：Agent 状态实时流"""
```

### 6.3 SSE 事件格式

```json
{
  "event": "step",
  "data": {
    "task_id": "task-123",
    "agent_id": "agent-456",
    "agent_role": "researcher",
    "step_type": "thought",
    "content": "我需要搜索 Python asyncio 的最佳实践",
    "timestamp": "2026-05-20T10:00:00Z"
  }
}
```

事件类型：
- `step` - 执行步骤更新
- `status` - 任务状态变更
- `error` - 错误事件
- `complete` - 任务完成

---

## 7. 前端设计

### 7.1 技术栈

- **框架**: React 18 + TypeScript
- **构建**: Vite（已有）
- **样式**: Tailwind CSS（需安装）
- **路由**: React Router v6（需安装）
- **状态**: Zustand（需安装）
- **HTTP**: Axios + SSE（需安装）

### 7.2 页面结构

| 路由 | 页面 | 功能 | Week |
|------|------|------|------|
| `/` | Dashboard | 任务统计、Agent 状态 | 2 |
| `/tasks` | TaskList | 任务列表 | 2 |
| `/tasks/:id` | TaskDetail | 任务详情 + 步骤可视化 | 2 |
| `/agents` | AgentMonitor | Agent 监控面板 | 3 |
| `/chat` | MultiAgentChat | 多 Agent 聊天室 | 3 |
| `/settings` | Settings | 设置 | 3 |

### 7.3 Store 设计

```typescript
// stores/taskStore.ts
interface TaskStore {
  tasks: Task[];
  currentTask: Task | null;
  steps: AgentStep[];
  isLoading: boolean;
  error: string | null;  // 错误状态，用于展示错误信息
  
  fetchTasks: () => Promise<void>;
  createTask: (description: string) => Promise<void>;
  fetchTaskDetail: (id: string) => Promise<void>;
  subscribeToTask: (id: string) => void;  // SSE 订阅
  clearError: () => void;  // 清除错误状态
}

// stores/agentStore.ts
interface AgentStore {
  agents: AgentState[];
  isLoading: boolean;
  error: string | null;  // 错误状态
  
  fetchAgents: () => Promise<void>;
  subscribeToAgents: () => void;
  clearError: () => void;
}
```

### 7.4 组件结构

```
src/
├── components/
│   └── layout/
│       ├── Sidebar.tsx       # 侧边栏导航
│       ├── Header.tsx        # 顶部栏
│       └── Layout.tsx        # 布局容器
├── pages/
│   ├── Dashboard.tsx         # 首页仪表盘
│   ├── Tasks.tsx             # 任务列表
│   └── TaskDetail.tsx        # 任务详情
├── stores/
│   ├── taskStore.ts
│   └── agentStore.ts
├── api/
│   └── client.ts             # Axios + SSE 封装
├── types/
│   └── index.ts              # TypeScript 类型定义
└── App.tsx                   # 路由配置
```

---

## 8. 测试策略

### 8.1 单元测试

| 模块 | 测试文件 | 关键测试点 | Day |
|------|---------|-----------|-----|
| Planner | `test_planner.py` | 3 种格式解析、循环依赖检测、回退机制 | 1 |
| Orchestrator | `test_orchestrator.py` | 并行执行、超时、取消、依赖顺序 | 5 |
| A2A Bus | `test_a2a_bus.py` | 点对点、广播、请求-响应、历史清理 | 3 |
| Agents | `test_agents.py` | 3 个角色创建、工具集、提示词 | 2 |
| Factory | `test_factory.py` | 角色创建、异常处理 | 2 |

### 8.2 集成测试（Day 6）

- **端到端任务执行**：创建任务 → 规划 → 执行 → 完成
- **多 Agent 协作**：Researcher → Executor
- **取消流程**：创建任务 → 取消 → 资源清理
- **SSE 流**：订阅任务 → 接收步骤事件 → 任务完成

### 8.3 前端测试（Week 3）

- 组件渲染测试
- Store 状态更新测试
- API 调用测试

---

## 9. 验收标准

### 9.1 功能验收（Day 7 演示清单）

- [ ] Planner 可解析 3 种格式变体（严格 JSON、宽松 JSON、自然语言）
- [ ] Planner 能检测循环依赖并抛出明确错误
- [ ] Planner 解析失败时回退到单任务模式
- [ ] Orchestrator 能并行执行无依赖任务（最多 3 个并发）
- [ ] Orchestrator 能按序执行有依赖任务
- [ ] Orchestrator 超时后优雅退出并清理资源
- [ ] Orchestrator 取消后停止所有子任务
- [ ] 3 个 Agent 角色可独立创建和执行
- [ ] AgentFactory 能创建所有已实现角色
- [ ] A2A 点对点消息可达
- [ ] A2A 广播消息可达
- [ ] WebSearch Mock 工具返回结果
- [ ] Calculator 工具能安全计算
- [ ] 前端 `npm run dev` 可正常启动
- [ ] 前端路由正常工作（/ → Dashboard, /tasks → Tasks）
- [ ] 前端 Tailwind 样式生效
- [ ] Zustand Stores 状态可更新
- [ ] POST /api/v1/tasks 能创建任务
- [ ] GET /api/v1/tasks/{id}/stream 返回 SSE 事件

### 9.2 质量验收

- [ ] 后端测试覆盖率 > 80%（Week 2 新模块）
- [ ] 所有单元测试通过
- [ ] black + isort 格式化通过
- [ ] mypy 类型检查通过
- [ ] 前端 ESLint 无错误

### 9.3 演示场景（Day 7）

**场景**：用户创建一个研究任务

```
用户输入: "研究 Python asyncio 最佳实践"

系统响应:
1. Planner 拆解为 3 个子任务:
   - [step-1] 搜索 asyncio 文档（Researcher）
   - [step-2] 搜索性能优化技巧（Researcher）
   - [step-3] 汇总最佳实践（Executor）

2. Orchestrator 执行:
   - Layer 1: step-1, step-2 并行执行
   - Layer 2: step-3 等待前两个完成

3. 前端实时显示:
   - 任务状态: pending → executing → completed
   - Agent 步骤: thought → action → observation → final
   - 最终结果: "Python asyncio 最佳实践包括..."
```

---

## 10. 与 Week 3 的衔接

### 10.1 Week 2 遗留到 Week 3

| 模块 | Week 2 状态 | Week 3 工作 |
|------|------------|------------|
| Agent 角色 | 3 个（Executor, Researcher, Planner） | 补充 Coder, Writer, Reviewer |
| 工具 | 2 个 Mock（WebSearch, Calculator） | 实现 8 个真实工具 |
| 前端页面 | Dashboard, Tasks, TaskDetail | AgentMonitor, Chat, Settings |
| API | 基础 CRUD + SSE | 认证、限流、高级查询 |

### 10.2 Week 3 新功能

- **Reflection 引擎**：Agent 自我反思和经验学习
- **完整工具集**：8 个 MCP 工具（WebSearch, Calculator, CodeExecute, FileIO, MemorySearch, AgentMessage, Summarize, WebBrowser）
- **RAG 系统**：向量检索增强
- **Memory 系统**：三层记忆（短期、长期、外部）
- **前端完整功能**：Agent 监控、多 Agent 聊天、知识库

---

## 附录

### A. 文件清单汇总

**Day 1**:
- `core/planner.py`
- `database/models.py`

**Day 2**:
- `agents/executor_agent.py`
- `agents/researcher_agent.py`
- `agents/factory.py`

**Day 3**:
- `core/a2a_bus.py`
- `tools/web_search.py`
- `tools/calculator.py`

**Day 4**:
- `frontend/package.json`（更新）
- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/components/layout/Header.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Tasks.tsx`
- `frontend/src/pages/TaskDetail.tsx`

**Day 5**:
- `core/orchestrator.py`

**Day 6**:
- `api/routes/tasks.py`
- `api/routes/agents.py`
- `tests/unit/test_planner.py`
- `tests/unit/test_orchestrator.py`
- `tests/unit/test_agents.py`
- `tests/integration/test_task_flow.py`

**Day 7**:
- 联调、Bug 修复、文档更新

### B. 依赖关系图

```
Week 2 模块依赖:

Planner (Day 1)
  └── 依赖: llm_client.py, schemas.py

ORM Models (Day 1)
  └── 依赖: database/connection.py

Agent Roles (Day 2)
  └── 依赖: agents/base.py, react_loop.py

A2A Bus (Day 3)
  └── 依赖: schemas.py

Tools (Day 3)
  └── 依赖: tools/base.py

Orchestrator (Day 5)
  └── 依赖: Planner, Agent Roles, A2A Bus, Tools

API Routes (Day 6)
  └── 依赖: Orchestrator, ORM Models

Frontend (Day 4)
  └── 独立，通过 API 对接
```

---

> **设计文档结束**
> 
> 下一步：调用 writing-plans skill 创建详细的文件级实施计划
