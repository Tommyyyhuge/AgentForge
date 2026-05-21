# AgentForge 模块划分文档 (Module Specification)
> **定位**：本项目的"架构宪法"。每个模块的边界、职责、接口、依赖在此严格定义。OpenCode 开发时必须遵循此文档，不得跨模块实现、不得遗漏接口。

---

## 架构原则

1. **单一职责**：一个模块只负责一个明确的功能域
2. **依赖单向**：上层可调下层，下层不可调上层
3. **接口契约**：模块间只能通过预定义的接口通信，禁止直接访问内部实现
4. **可扩展**：新增功能应通过"新增模块"或"扩展现有模块接口"实现，不应修改已有核心逻辑

---

## 模块总览

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 4: 表现层 (Presentation)                              │
│ frontend/src/components/       — UI 组件                    │
│ frontend/src/pages/            — 页面组装                    │
│ frontend/src/stores/           — 状态管理                    │
│ frontend/src/api/              — HTTP 客户端                 │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: 网关层 (Gateway)                                   │
│ backend/agent_forge/api/       — FastAPI 路由 + SSE         │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: 业务核心层 (Core)                                  │
│ backend/agent_forge/core/      — 八大方向引擎实现            │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: 能力层 (Capability)                                │
│ backend/agent_forge/agents/    — Agent 角色实现              │
│ backend/agent_forge/mcp/       — MCP 工具注册               │
│ backend/agent_forge/tools/     — 工具实现                    │
├─────────────────────────────────────────────────────────────┤
│ Layer 0: 基础设施层 (Infrastructure)                        │
│ backend/agent_forge/models/    — 数据模型（类型契约）        │
│ backend/agent_forge/database/  — 数据库初始化               │
│ backend/agent_forge/config/    — 配置管理                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 模块清单（共 20 个模块）

| # | 模块名 | 路径 | 职责 | 所属层 |
|---|--------|------|------|--------|
| M01 | 数据模型 | `models/schemas.py` | 全项目类型契约 | Layer 0 |
| M02 | 数据库初始化 | `database/init_db.py` | SQLite 表创建 | Layer 0 |
| M03 | 配置管理 | `config/settings.py` | 环境变量 + 常量 | Layer 0 |
| M04 | LLM 客户端 | `core/llm_client.py` | 统一调用 Kimi/DeepSeek | Layer 2 |
| M05 | ReAct 引擎 | `core/react_loop.py` | 推理循环实现 | Layer 2 |
| M06 | 规划器 | `core/planner.py` | 任务拆解 + 依赖图 | Layer 2 |
| M07 | 调度器 | `core/orchestrator.py` | Agent 调度 + 状态机 | Layer 2 |
| M08 | 反思引擎 | `core/reflection_engine.py` | 自我评估 | Layer 2 |
| M09 | A2A 总线 | `core/a2a_bus.py` | Agent 间通信 | Layer 2 |
| M10 | RAG 系统 | `core/rag_system.py` | 向量检索 | Layer 2 |
| M11 | 记忆管理 | `core/memory_manager.py` | 三层记忆协调 | Layer 2 |
| M12 | Agent 基类 | `agents/base.py` | 抽象基类 + 执行流程 | Layer 1 |
| M13 | 角色实现 | `agents/*_agent.py` | 6 个具体角色 | Layer 1 |
| M14 | MCP 注册中心 | `mcp/tool_registry.py` | 工具发现 + 调用 | Layer 1 |
| M15 | 工具实现 | `tools/*.py` | 4 个内置工具 | Layer 1 |
| M16 | API 路由 | `api/main.py` | FastAPI 应用 + CORS | Layer 3 |
| M17 | 任务 API | `api/tasks.py` | 任务 CRUD + SSE | Layer 3 |
| M18 | 状态管理 | `stores/taskStore.ts` | Zustand 全局状态 | Layer 4 |
| M19 | HTTP 客户端 | `api/taskApi.ts` | Axios/Fetch 封装 | Layer 4 |
| M20 | UI 组件 | `components/*.tsx` | 6 个展示组件 | Layer 4 |

---

## 逐模块详细定义

---

### M01 — 数据模型 (models/schemas.py)

**一句话职责**：全项目所有数据结构的单一真相源。

**包含内容**：

```python
# === 枚举 ===
class TaskStatus(str, Enum):           # pending/waiting/running/completed/failed/retrying
class MessageType(str, Enum):          # task/result/query/feedback/handoff
class EventType(str, Enum):            # thought/action/observation/final/error/plan_created/...

# === 基础模型 ===
class Task(BaseModel):                 # 主任务
class SubTask(BaseModel):              # 子任务（含 dependencies 依赖列表）
class Step(BaseModel):                 # ReAct 单步
class ToolCall(BaseModel):             # 工具调用描述
class ToolResult(BaseModel):           # 工具返回结果
class ToolSchema(BaseModel):           # 工具 JSON Schema 描述
class ExecutionResult(BaseModel):      # Agent 执行结果
class StepEvent(BaseModel):            # SSE 流式事件
class ReflectionReport(BaseModel):     # 反思报告
class AgentMessage(BaseModel):         # A2A 消息
class Plan(BaseModel):                 # 执行计划（含子任务列表）
class Document(BaseModel):             # RAG 文档
class RetrievalResult(BaseModel):      # RAG 检索结果
class MemoryEntry(BaseModel):          # 记忆条目
class ExperienceEntry(BaseModel):      # 经验条目
```

**模块边界**：
- ✅ 做：所有 Pydantic 模型定义、枚举定义
- ❌ 不做：任何业务逻辑、数据库操作、LLM 调用

**输出接口**：被所有其他模块 `import`

---

### M02 — 数据库初始化 (database/init_db.py)

**一句话职责**：创建 SQLite 数据库和表结构，只运行一次。

**包含表**：

```sql
tasks          — 主任务
subtasks       — 子任务
agent_executions — Agent 执行记录
memories       — 长期记忆（含 embedding_json 向量字段）
experiences    — 经验记忆
```

**模块边界**：
- ✅ 做：建表、建索引
- ❌ 不做：任何增删改查操作（这些在 Memory 模块里）

**输出接口**：`async def init_database(db_path: str)` — 幂等，可多次调用

---

### M03 — 配置管理 (config/settings.py)

**一句话职责**：从环境变量读取配置，集中管理常量。

**包含配置项**：

```python
KIMI_API_KEY: str                    # 从 env 读取
DEEPSEEK_API_KEY: str                # 从 env 读取
DEFAULT_LLM_MODEL: str               # "kimi-k2-6" 或 "deepseek-chat"
MAX_REACT_STEPS: int = 10            # ReAct 最大步数
MAX_RETRY: int = 3                   # LLM 重试次数
REQUEST_TIMEOUT: int = 60            # 请求超时秒数
DATABASE_PATH: str = "./data/agent_forge.db"
FAISS_INDEX_PATH: str = "./data/faiss.index"
```

**模块边界**：
- ✅ 做：读取 env、默认值、类型转换
- ❌ 不做：任何业务逻辑

---

### M04 — LLM 客户端 (core/llm_client.py)

**一句话职责**：封装 Kimi 和 DeepSeek 的 OpenAI 兼容接口，统一对外提供 chat 和 embed。

**类定义**：

```python
class LLMClient:
    def __init__(self, model: str, api_key: str, base_url: str)
    
    # 对话（支持流式）
    async def chat(
        self,
        messages: List[dict],
        temperature: float = 0.7,
        stream: bool = False
    ) -> Union[str, AsyncGenerator[str]]
    
    # 向量化（用于 RAG）
    async def embed(self, texts: List[str]) -> List[List[float]]
    
    # 重试 + 超时封装（内部实现，不暴露）
```

**模块边界**：
- ✅ 做：HTTP 请求、流式解析、重试、超时、embedding
- ❌ 不做：Prompt 模板、业务逻辑、状态管理

**输入依赖**：M03 (配置)
**输出接口**：被 M05/M06/M08/M10/M12 调用

---

### M05 — ReAct 引擎 (core/react_loop.py)

**一句话职责**：实现 ReAct 推理循环，是 Agent 的"大脑执行器"。

**类定义**：

```python
class ReActLoop:
    def __init__(
        self,
        agent_name: str,               # 哪个 Agent 在运行
        system_prompt: str,            # Agent 的系统提示词
        tools: List[ToolSchema],       # 可用工具列表（从 MCP 获取）
        llm: LLMClient,                # LLM 客户端实例
        max_steps: int = 10            # 最大步数
    )
    
    # 核心：运行 ReAct 循环，流式返回事件
    async def run(
        self,
        task: str,
        context: Optional[str] = None   # 额外上下文（如 RAG 结果、记忆）
    ) -> AsyncGenerator[StepEvent, None]
    
    # 内部方法（私有）
    def _build_prompt(self, ...) -> str        # 构建 LLM 提示词
    def _parse_response(self, ...) -> ParsedAction  # 解析 Thought/Action
    async def _execute_tool(self, ...) -> str        # 执行工具调用
```

**LLM 输出格式约定**（必须在 Prompt 中强制要求）：

```
## Thought
[思考内容，必须存在]

## Action
{"tool": "工具名", "arguments": {...}}

## Observation
[工具返回结果，由系统填充]

## Final Answer
[最终答案，出现时循环结束]
```

**模块边界**：
- ✅ 做：ReAct 循环、流式解析、工具调用分发、步数限制
- ❌ 不做：工具的具体实现（调用 ToolRegistry）、记忆存储、Agent 间通信

**输入依赖**：M01 (模型), M04 (LLM), M14 (ToolSchema)
**输出接口**：`AsyncGenerator[StepEvent]` — 流式事件

---

### M06 — 规划器 (core/planner.py)

**一句话职责**：将用户任务拆解为带依赖关系的子任务 DAG。

**类定义**：

```python
class Planner:
    def __init__(self, llm: LLMClient)
    
    # 生成执行计划
    async def plan(self, task: str) -> Plan
    
    # 内部：构建规划 Prompt
    def _build_plan_prompt(self, task: str) -> str
    
    # 内部：解析 LLM 输出的 JSON 为 Plan 对象
    def _parse_plan(self, raw: str) -> Plan
```

**规划 Prompt 中可用的 Agent 角色清单**（硬编码）：

```
- researcher: 信息搜索和资料整理（工具: web_search, browser）
- coder: 编写和执行代码（工具: code_executor, calculator）
- writer: 撰写报告和文案（工具: 无）
- reviewer: 质量审查（工具: 无）
```

**模块边界**：
- ✅ 做：任务分析、子任务拆解、依赖关系构建、复杂度评估
- ❌ 不做：实际执行、调度、Agent 创建

**输入依赖**：M01 (Plan/SubTask), M04 (LLM)
**输出接口**：`Plan` 对象

---

### M07 — 调度器 (core/orchestrator.py)

**一句话职责**：根据 Plan 的依赖图，调度 Agent 执行，管理整个任务生命周期。

**类定义**：

```python
class Orchestrator:
    def __init__(
        self,
        planner: Planner,
        agent_factory: AgentFactory,   # 创建 Agent 的工厂
        a2a_bus: A2ABus                # A2A 通信总线
    )
    
    # 核心：执行完整计划
    async def execute(
        self,
        task_id: str,
        plan: Plan
    ) -> AsyncGenerator[OrchestratorEvent, None]
    
    # 内部：执行单个子任务
    async def _execute_subtask(self, subtask: SubTask) -> SubTaskResult
    
    # 内部：构建 DAG + 拓扑排序
    def _build_execution_waves(self, subtasks: List[SubTask]) -> List[List[SubTask]]
    
    # 内部：失败重试
    async def _retry_subtask(self, subtask: SubTask, attempt: int) -> SubTaskResult
```

**事件类型**：

```python
class OrchestratorEvent(BaseModel):
    type: Literal[
        "plan_started",
        "subtask_started", "subtask_completed", "subtask_failed", "subtask_retried",
        "agent_started", "agent_completed", "agent_failed",
        "plan_completed", "plan_failed"
    ]
    data: dict
    timestamp: datetime
```

**模块边界**：
- ✅ 做：DAG 构建、拓扑排序、并行调度、失败重试、事件流
- ❌ 不做：ReAct 具体推理（调 M05）、工具执行（调 M14）、Agent 内部逻辑

**输入依赖**：M01, M06, M09, M12
**输出接口**：`AsyncGenerator[OrchestratorEvent]`

---

### M08 — 反思引擎 (core/reflection_engine.py)

**一句话职责**：Agent 完成任务后的自我评估，生成结构化反思报告。

**类定义**：

```python
class ReflectionEngine:
    def __init__(self, llm: LLMClient)
    
    # 对执行结果进行反思
    async def reflect(self, result: ExecutionResult) -> ReflectionReport
    
    # 内部：构建反思 Prompt
    def _build_reflection_prompt(self, result: ExecutionResult) -> str
```

**反思维度**（Prompt 中要求 LLM 按此评分）：

| 维度 | 说明 | 权重 |
|------|------|------|
| efficiency | 执行效率 | 20% |
| decision | 决策质量 | 25% |
| error_handling | 错误处理 | 20% |
| output_quality | 输出质量 | 35% |

**模块边界**：
- ✅ 做：生成反思 Prompt、调用 LLM、解析反思报告
- ❌ 不做：存储反思结果（调 M11）、修改 Agent 行为

**输入依赖**：M01, M04
**输出接口**：`ReflectionReport`

---

### M09 — A2A 总线 (core/a2a_bus.py)

**一句话职责**：Agent 间通信的"邮局"——注册、发现、路由消息。

**类定义**：

```python
class A2ABus:
    def __init__(self)
    
    # 注册 Agent
    def register(self, agent_id: str, capabilities: List[str], agent_ref: BaseAgent)
    
    # 发现 Agent（按能力）
    def discover(self, capability: Optional[str] = None) -> List[AgentInfo]
    
    # 发送消息
    async def send(self, message: AgentMessage) -> bool
    
    # 任务移交（核心功能）
    async def handoff(
        self,
        from_agent: str,
        to_agent: str,
        task: str,
        context: Optional[dict] = None
    ) -> str
    
    # 获取消息队列
    def get_queue(self, agent_id: str) -> asyncio.Queue
```

**模块边界**：
- ✅ 做：Agent 注册、能力发现、消息路由、任务移交
- ❌ 不做：Agent 具体执行、业务逻辑

**输入依赖**：M01
**输出接口**：`AgentMessage` 路由，`handoff` 返回结果字符串

---

### M10 — RAG 系统 (core/rag_system.py)

**一句话职责**：文档向量化存储 + 相似度检索。

**类定义**：

```python
class RAGSystem:
    def __init__(self, llm: LLMClient, index_path: Optional[str] = None)
    
    # 添加文档
    async def add_documents(self, documents: List[Document])
    
    # 检索
    async def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]
    
    # 内部：切分文档
    def _chunk(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]
    
    # 内部：保存/加载 FAISS 索引
    def _save_index(self)
    def _load_index(self)
```

**模块边界**：
- ✅ 做：文档切分、向量化、FAISS 索引、相似度检索
- ❌ 不做：文档来源获取（外部传入）、Agent 集成（外部调用）

**输入依赖**：M01, M04
**输出接口**：`List[RetrievalResult]`

---

### M11 — 记忆管理 (core/memory_manager.py + 3 个子模块)

**一句话职责**：协调三层记忆（短期/长期/经验），对外提供统一接口。

**文件结构**：

```
core/
├── memory_manager.py      # 协调器（统一入口）
├── short_term_memory.py   # 短期记忆（内存，当前任务上下文）
├── long_term_memory.py    # 长期记忆（SQLite + 关键词检索）
└── experience_memory.py   # 经验记忆（SQLite，Reflection 总结）
```

**统一接口**（MemoryManager 类）：

```python
class MemoryManager:
    def __init__(self, db_path: str)
    
    # 存储执行结果到三层记忆
    async def store(self, task: str, result: ExecutionResult)
    
    # 从三层记忆检索相关信息
    async def search(self, query: str, top_k: int = 3) -> List[Union[MemoryEntry, ExperienceEntry]]
    
    # 短期记忆专用：追加当前轮次
    def add_turn(self, result: ExecutionResult)
    
    # 短期记忆专用：获取当前上下文
    def get_context(self) -> str
    
    # 经验记忆专用：存储反思
    async def store_experience(self, reflection: ReflectionReport)
```

**三层记忆对比**：

| 维度 | 短期记忆 | 长期记忆 | 经验记忆 |
|------|----------|----------|----------|
| 存储 | 内存（Python list） | SQLite | SQLite |
| 检索 | 关键词匹配 | 关键词 + 分数排序 | 关键词匹配 |
| 内容 | 当前任务的执行步骤 | 历史任务记录 | Reflection 总结 |
| 容量 | 最近 20 轮 | 无限制 | 无限制 |
| 持久化 | 否 | 是 | 是 |

**模块边界**：
- ✅ 做：三层记忆的存储和检索、统一接口
- ❌ 不做：RAG 向量检索（调 M10）、LLM 调用

**输入依赖**：M01, M02
**输出接口**：`List[MemoryEntry]`, `str` (上下文)

---

### M12 — Agent 基类 (agents/base.py)

**一句话职责**：所有 Agent 角色的抽象模板，定义执行流程。

**类定义**：

```python
class BaseAgent(ABC):
    # === 子类必须实现的属性 ===
    name: str                          # Agent 名称
    role: str                          # 角色描述
    system_prompt: str                 # 系统提示词
    available_tools: List[str]         # 可用工具名列表
    
    # === 初始化注入 ===
    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        memory: MemoryManager,
        a2a_bus: A2ABus
    )
    
    # === 核心执行流程（模板方法模式，子类一般不覆盖）===
    async def execute(self, task: str, context: Optional[dict] = None) -> ExecutionResult:
        # 1. 从记忆检索相关经验
        # 2. 构建上下文
        # 3. 获取工具 Schema 列表
        # 4. 创建 ReActLoop 并运行
        # 5. 执行 Reflection
        # 6. 存储到记忆
        # 7. 返回结果
        pass
    
    # === A2A 通信 ===
    async def send_message(self, target: str, content: str, msg_type: str = "task")
    async def receive_message(self) -> Optional[AgentMessage]
    
    # === 内部 ===
    async def _reflect(self, result: ExecutionResult) -> Optional[ReflectionReport]
```

**模块边界**：
- ✅ 做：执行流程编排、记忆集成、ReAct 调用、Reflection 调用、A2A 通信
- ❌ 不做：具体系统提示词（子类定义）、具体工具选择（通过 available_tools 声明）

**输入依赖**：M01, M04, M05, M08, M09, M11, M14
**输出接口**：`ExecutionResult`

---

### M13 — 角色实现 (agents/*_agent.py)

**一句话职责**：6 个具体 Agent 角色，只定义系统提示词和可用工具。

| 文件 | 类名 | 系统提示词重点 | 可用工具 |
|------|------|---------------|----------|
| `planner_agent.py` | PlannerAgent | 任务拆解、依赖分析 | 无 |
| `researcher_agent.py` | ResearcherAgent | 搜索策略、信息筛选 | web_search, browser |
| `coder_agent.py` | CoderAgent | 代码质量、错误处理 | code_executor, calculator |
| `writer_agent.py` | WriterAgent | 结构化写作、逻辑清晰 | 无 |
| `reviewer_agent.py` | ReviewerAgent | 事实核查、质量评估 | 无 |
| `executor_agent.py` | ExecutorAgent | 工具调用、执行操作 | 全部工具 |

**每个角色的代码模板**：

```python
class XxxAgent(BaseAgent):
    name = "xxx"
    role = "xxx"
    available_tools = ["tool1", "tool2"]
    
    system_prompt = """
    你是 xxx 角色。...
    
    工作原则：
    1. ...
    2. ...
    
    输出格式要求：
    ...
    """
```

**模块边界**：
- ✅ 做：定义角色属性、系统提示词
- ❌ 不做：任何业务逻辑（全在基类里）

**输入依赖**：M12 (继承)
**输出接口**：通过 `execute()` 返回 `ExecutionResult`

---

### M14 — MCP 注册中心 (mcp/tool_registry.py)

**一句话职责**：工具的"工商局"——注册、发现、调用、参数校验。

**类定义**：

```python
class ToolRegistry:
    _instance = None  # 单例
    
    def __init__(self)
    
    # 装饰器注册
    def register(self, tool_class: Type[Tool]) -> Type[Tool]
    
    # 获取所有工具 Schema（MCP discover）
    def discover(self) -> List[ToolSchema]
    
    # 获取单个工具 Schema
    def get_schema(self, tool_name: str) -> ToolSchema
    
    # 调用工具（MCP invoke）
    async def invoke(self, tool_name: str, arguments: dict) -> ToolResult
    
    # 参数校验
    def validate(self, tool_name: str, arguments: dict) -> Tuple[bool, Optional[str]]
```

**模块边界**：
- ✅ 做：装饰器注册、Schema 管理、参数校验、调用分发
- ❌ 不做：工具的具体实现（在 M15）

**输入依赖**：M01
**输出接口**：`List[ToolSchema]`, `ToolResult`

---

### M15 — 工具实现 (tools/*.py)

**一句话职责**：4 个内置工具的具体实现。

| 文件 | 类名 | 功能 | 安全限制 |
|------|------|------|----------|
| `web_search.py` | WebSearchTool | DuckDuckGo 搜索 | 无 |
| `calculator.py` | CalculatorTool | 安全数学计算 | 仅允许 math 运算符 |
| `code_executor.py` | CodeExecutorTool | 子进程执行 Python | 超时 30s，禁止危险 import |
| `browser.py` | BrowserTool | 抓取网页内容 | 仅 GET 请求，超时 10s |

**每个工具的代码模板**：

```python
@registry.register  # MCP 装饰器注册
class XxxTool(Tool):
    name = "xxx"
    description = "..."
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(...)
    
    async def execute(self, **kwargs) -> str:
        # 具体实现
        pass
```

**模块边界**：
- ✅ 做：工具的具体执行逻辑
- ❌ 不做：注册逻辑（装饰器处理）、调用分发（M14 处理）

**输入依赖**：M14 (装饰器)
**输出接口**：`str` (工具执行结果)

---

### M16 — API 路由主入口 (api/main.py)

**一句话职责**：FastAPI 应用实例，挂载所有子路由，配置 CORS。

**包含内容**：

```python
app = FastAPI(title="AgentForge", version="1.0")

# CORS 配置
app.add_middleware(CORSMiddleware, ...)

# 挂载路由
app.include_router(tasks_router, prefix="/api/tasks")
app.include_router(tools_router, prefix="/api/tools")
app.include_router(memory_router, prefix="/api/memory")

# 健康检查
@app.get("/health")
```

**模块边界**：
- ✅ 做：应用创建、中间件、路由挂载
- ❌ 不做：具体路由处理（在 M17）

---

### M17 — 任务 API (api/tasks.py)

**一句话职责**：任务相关的 HTTP 接口 + SSE 流式推送。

**接口清单**：

| 方法 | 路径 | 功能 | SSE? |
|------|------|------|------|
| POST | `/api/tasks` | 创建任务 | 否 |
| GET | `/api/tasks/{id}` | 获取任务详情 | 否 |
| GET | `/api/tasks/{id}/stream` | **SSE 流式执行** | ✅ |
| GET | `/api/tasks/{id}/plan` | 获取执行计划 | 否 |
| GET | `/api/tasks/{id}/result` | 获取最终结果 | 否 |
| GET | `/api/tasks/{id}/agents` | 获取 Agent 执行记录 | 否 |
| GET | `/api/tasks/{id}/reflect` | 获取反思报告 | 否 |
| POST | `/api/agents/{id}/message` | Agent 间通信 (A2A) | 否 |

**SSE 事件流格式**：

```
data: {"type": "plan_created", "data": {...}, "timestamp": "..."}

data: {"type": "agent_started", "data": {"agent": "researcher", ...}}

data: {"type": "thought", "data": {"agent": "researcher", "content": "...", "step": 1}}

data: {"type": "action", "data": {"agent": "researcher", "tool": "web_search", "args": {...}}}

data: {"type": "observation", "data": {"agent": "researcher", "result": "..."}}

data: {"type": "agent_completed", "data": {"agent": "researcher", "result": "..."}}

data: {"type": "final_result", "data": "最终答案..."}
```

**模块边界**：
- ✅ 做：HTTP 请求解析、SSE 流封装、路由处理
- ❌ 不做：业务逻辑（调 M06/M07）

**输入依赖**：M01, M06, M07, M09, M11

---

### M18 — 状态管理 (stores/taskStore.ts)

**一句话职责**：前端全局状态，管理任务生命周期 + SSE 连接。

```typescript
interface TaskStore {
  // 状态
  currentTask: Task | null;
  plan: Plan | null;
  agents: AgentExecution[];
  events: StepEvent[];
  toolCalls: ToolCallLog[];
  reflection: ReflectionReport | null;
  isRunning: boolean;
  error: string | null;
  
  // 方法
  createTask: (task: string) => Promise<string>;
  connectSSE: (taskId: string) => void;
  disconnectSSE: () => void;
  reset: () => void;
}
```

**模块边界**：
- ✅ 做：状态存储、SSE 事件处理、状态转换
- ❌ 不做：HTTP 请求（调 M19）、UI 渲染

---

### M19 — HTTP 客户端 (api/taskApi.ts)

**一句话职责**：封装后端 API 调用。

```typescript
const taskApi = {
  createTask: (task: string) => Promise<{ taskId: string }>;
  getTask: (taskId: string) => Promise<Task>;
  getPlan: (taskId: string) => Promise<Plan>;
  getResult: (taskId: string) => Promise<string>;
  getReflection: (taskId: string) => Promise<ReflectionReport>;
  connectSSE: (taskId: string, onMessage: (e: StepEvent) => void) => EventSource;
};
```

**模块边界**：
- ✅ 做：HTTP 请求、SSE 连接管理
- ❌ 不做：状态管理（调 M18）

---

### M20 — UI 组件 (components/*.tsx)

**一句话职责**：6 个展示组件，纯展示 + 交互，无业务逻辑。

| 组件 | 文件 | 职责 | 数据来源 |
|------|------|------|----------|
| TaskInput | `TaskInput.tsx` | 任务输入 + 场景选择 | taskStore |
| TaskPlan | `TaskPlan.tsx` | 子任务列表 + 依赖图 | taskStore.plan |
| AgentMonitor | `AgentMonitor.tsx` | **核心**：ReAct 实时展示 | taskStore.events |
| CollaborationGraph | `CollaborationGraph.tsx` | Agent 协作流程图 | taskStore.agents + events |
| ToolLog | `ToolLog.tsx` | 工具调用时间线 | taskStore.toolCalls |
| ReflectionReport | `ReflectionReport.tsx` | 反思报告展示 | taskStore.reflection |

**模块边界**：
- ✅ 做：UI 渲染、用户交互、动画效果
- ❌ 不做：数据获取（调 M18/M19）、状态管理

---

## 模块依赖矩阵

```
        M01   M02   M03   M04   M05   M06   M07   M08   M09   M10   M11   M12   M13   M14   M15   M16   M17   M18   M19   M20
M01      -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M02     imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M03     imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M04     imp   -    imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M05     imp    -     -    imp    -     -     -     -     -     -     -     -     -    imp    -     -     -     -     -     -
M06     imp    -     -    imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M07     imp    -     -     -     -    imp    -     -    imp    -     -    imp   imp    -     -     -     -     -     -     -
M08     imp    -     -    imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M09     imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M10     imp    -     -    imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M11     imp   imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M12     imp    -     -    imp   imp    -     -    imp   imp   -    imp    -     -    imp    -     -     -     -     -     -
M13     imp    -     -     -     -     -     -     -     -     -     -    imp    -     -     -     -     -     -     -     -
M14     imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -
M15     imp    -     -     -     -     -     -     -     -     -     -     -     -    imp    -     -     -     -     -     -
M16     imp    -     -     -     -     -     -     -     -     -     -     -     -     -     -     -    imp    -     -     -
M17     imp    -     -     -     -    imp   imp    -     -     -    imp    -     -     -     -     -     -     -     -     -
M18      -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -    imp    -
M19      -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -    imp
M20      -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -     -    imp    -     -
```

> `imp` = import / 依赖。M01 被最多模块依赖（14 个），是项目的类型契约中心。

---

## OpenCode 开发顺序（按依赖拓扑排序）

```
第一批（无依赖，可并行）：
  M01 数据模型 → M02 数据库初始化 → M03 配置管理

第二批（依赖第一批）：
  M04 LLM 客户端 → M14 MCP 注册中心 → M15 工具实现

第三批（依赖第二批）：
  M05 ReAct 引擎 → M06 规划器 → M08 反思引擎
  M09 A2A 总线 → M10 RAG 系统 → M11 记忆管理

第四批（依赖第三批）：
  M12 Agent 基类 → M13 角色实现

第五批（依赖第四批）：
  M07 调度器

第六批（依赖第五批）：
  M17 任务 API → M16 API 主入口

第七批（前端，独立）：
  M19 HTTP 客户端 → M18 状态管理 → M20 UI 组件
```

---

## 新增功能时的模块选择指南

| 想加的功能 | 修改/新增哪个模块 | 不需要碰的模块 |
|-----------|-----------------|---------------|
| 新增 Agent 角色 | M13 (新增文件) | M05/M07/M12 等核心模块 |
| 新增工具 | M15 (新增文件) | M14 自动适配 |
| 新增 LLM 提供商 | M04 | 其他全部 |
| 新增前端组件 | M20 | 后端全部 |
| 调整反思维度 | M08 | 其他模块 |
| 更换向量数据库 | M10 | 其他模块 |
| 新增 API 端点 | M17 | 业务逻辑层 |

---

> **本文档为架构宪法，开发过程中不得擅自修改模块边界。如需调整，先更新本文档，再同步修改代码。**
