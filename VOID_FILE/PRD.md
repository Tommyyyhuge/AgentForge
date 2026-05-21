# AgentForge 产品需求文档 (PRD)
> **项目定位**：全功能多智能体协作平台 —— 覆盖 ReAct、Plan-and-Solve、Reflection、Multi-Agent、MCP、A2A、RAG、Memory 八大核心方向的面试级 Demo
> **目标用户**：面试官、技术同行（展示全栈 + Agent 系统设计与工程能力）
> **技术栈**：React 18 + TypeScript + Tailwind + FastAPI + Python + Kimi K2.6 / DeepSeek
> **开发周期**：6-7 周

---

## 1. 产品概述

### 1.1 产品定位

AgentForge 是一个**全功能多智能体协作任务执行平台**。用户输入复杂任务后，系统自动进行任务规划（Plan-and-Solve），由专门的 Agent 角色通过 ReAct 推理循环协作执行，期间支持工具调用（MCP 风格注册）、记忆检索（RAG + Memory）、Agent 间通信（A2A 风格），并在执行后进行自我反思（Reflection）。

### 1.2 核心亮点（面试时可强调）

| 亮点 | 说明 |
|------|------|
| **手写 ReAct 引擎** | 从零实现完整的 Reasoning + Acting 循环，非调用现成框架 |
| **多 Agent 协作调度器** | 自研 Orchestrator，支持依赖图执行、并行调度、状态机管理 |
| **MCP 工具注册体系** | 简化版 Model Context Protocol，工具自动发现、统一调用 |
| **A2A 风格 Agent 通信** | Agent 间通过标准化消息协议协作，展示协议理解 |
| **完整记忆系统** | 短期记忆（对话历史）+ 长期记忆（向量检索 RAG）+ 经验记忆（Reflection） |
| **流式可视化** | SSE 实时推送 Agent 思维链，前端完整展示思考过程 |

### 1.3 面试展示路径

```
1. 打开 Web Demo → 看到专业的 Dashboard 界面
2. 选择预设场景（调研/编程/写作）或输入自定义任务
3. 点击执行 → 实时看到 Planner 拆解任务
4. 观看多个 Agent 协作 → ReAct 循环可视化
5. 查看协作流程图 → Agent 间如何传递消息
6. 查看工具调用日志 → MCP 风格注册的工具被调用
7. 查看反思报告 → Agent 自我评估和改进建议
8. 最终输出完整的执行报告
```

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (React 18)                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ 任务输入 │ │ 计划展示 │ │ Agent监控│ │ 协作流程图       │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ 工具日志 │ │ 记忆检索 │ │ 反思报告 │ │ 结果展示         │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │ SSE (Server-Sent Events)
┌─────────────────────────┼───────────────────────────────────┐
│                      后端 (FastAPI)                         │
│  ┌──────────────────────┴──────────────────────────────┐   │
│  │              API 层                                  │   │
│  │  POST /tasks              - 创建任务                │   │
│  │  GET  /tasks/{id}         - 获取任务状态            │   │
│  │  GET  /tasks/{id}/stream  - SSE 流式执行            │   │
│  │  GET  /tasks/{id}/plan    - 获取执行计划            │   │
│  │  GET  /tasks/{id}/agents  - 获取 Agent 执行记录      │   │
│  │  GET  /tasks/{id}/result  - 获取最终结果            │   │
│  │  GET  /tasks/{id}/reflect - 获取反思报告            │   │
│  │  POST /agents/{id}/message - Agent 间通信 (A2A)     │   │
│  │  GET  /tools              - 列出可用工具 (MCP)      │   │
│  │  GET  /memory/search      - 记忆检索 (RAG)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│  ┌───────────────────────┼──────────────────────────────┐  │
│  │              AgentForge 核心引擎                        │  │
│  │                                                       │  │
│  │  ┌─────────────┐    ┌─────────────────────────────┐  │  │
│  │  │ Planner     │    │      Orchestrator 调度器      │  │  │
│  │  │ (Plan-and-  │───→│  - 依赖图构建                 │  │  │
│  │  │   Solve)    │    │  - 状态机管理 (pending/        │  │  │
│  │  └─────────────┘    │    running/completed/failed)  │  │  │
│  │                     │  - 并行调度                     │  │  │
│  │  ┌─────────────────┐│  - Agent 生命周期管理           │  │  │
│  │  │ Agent 角色池     ││                               │  │  │
│  │  │ - PlannerAgent  ││  ┌─────────────┐  ┌─────────┐ │  │  │
│  │  │ - Researcher    ││  │  ReAct 引擎  │  │ Reflection│ │  │  │
│  │  │ - CoderAgent    ││  │  - Thought   │  │ 引擎      │ │  │  │
│  │  │ - WriterAgent   ││  │  - Action    │  │ - 自评    │ │  │  │
│  │  │ - ReviewerAgent ││  │  - Observation│ │ - 总结    │ │  │  │
│  │  │ - ExecutorAgent ││  │  - 循环控制  │  │ - 建议    │ │  │  │
│  │  └─────────────────┘│  └─────────────┘  └─────────┘ │  │  │
│  └─────────────────────┴───────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────┼──────────────────────────────┐  │
│  │              基础设施层                                 │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │  │
│  │  │ MCP 工具注册  │  │ A2A 消息总线  │  │ 记忆系统      │  │  │
│  │  │ - 工具发现    │  │ - Agent 寻址  │  │ - 短期记忆    │  │  │
│  │  │ - 参数校验    │  │ - 消息路由    │  │ - 长期记忆    │  │  │
│  │  │ - 统一调用    │  │ - 异步通信    │  │ - 向量检索    │  │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │ LLM 适配层 (Kimi K2.6 / DeepSeek)                │  │  │
│  │  │ - OpenAI 兼容接口                                 │  │  │
│  │  │ - 流式输出                                        │  │  │
│  │  │ - 多模型切换                                      │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端框架 | React | 18.3+ |
| 前端语言 | TypeScript | 5.5+ |
| 样式方案 | Tailwind CSS | 3.4+ |
| 构建工具 | Vite | 6.0+ |
| UI 组件 | shadcn/ui | latest |
| 状态管理 | Zustand | 4.5+ |
| 流程图 | @xyflow/react (ReactFlow) | 12.0+ |
| 后端框架 | FastAPI | 0.115+ |
| 后端语言 | Python | 3.11+ |
| LLM SDK | OpenAI (兼容接口) | 1.60+ |
| 向量库 | FAISS (CPU) | 1.8+ |
| 数据模型 | Pydantic | 2.10+ |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | 3.45+ |
| 部署 | Docker + Docker Compose | 24+ |

---

## 3. 核心功能模块详细设计

### 3.1 ReAct 引擎（P0 - 必做）

#### 3.1.1 核心循环

```python
class ReActLoop:
    """
    ReAct 推理循环实现
    
    每一轮循环执行：
    1. 构建提示词（系统提示 + 任务描述 + 可用工具 + 历史步骤）
    2. 调用 LLM 生成响应
    3. 解析响应，提取 Thought + Action
    4. 执行 Action（调用工具或直接回答）
    5. 获取 Observation
    6. 判断是否结束（Final Answer）
    7. 存储 Step 到记忆
    """
    
    def __init__(
        self,
        agent_name: str,           # Agent 名称
        system_prompt: str,        # Agent 系统提示词
        tools: List[ToolSchema],   # 可用工具 Schema 列表
        llm: LLMClient,            # LLM 客户端
        max_steps: int = 10        # 最大步数限制
    ):
        self.agent_name = agent_name
        self.system_prompt = system_prompt
        self.tools = tools
        self.llm = llm
        self.max_steps = max_steps
        self.steps: List[Step] = []  # 执行历史
    
    async def run(self, task: str, context: Optional[str] = None) -> AsyncGenerator[StepEvent, None]:
        """运行 ReAct 循环直到完成或达到最大步数"""
        for step_num in range(self.max_steps):
            # 构建提示词
            prompt = self._build_prompt(task, context, step_num)
            
            # 调用 LLM（流式）
            response = await self.llm.chat(
                messages=[{"role": "system", "content": self.system_prompt},
                          {"role": "user", "content": prompt}],
                stream=True
            )
            
            # 流式解析
            async for chunk in response:
                parsed = self._parse_response(chunk)
                
                if parsed.thought:
                    yield StepEvent(type="thought", content=parsed.thought, step_number=step_num, timestamp=datetime.now())
                
                if parsed.action:
                    yield StepEvent(type="action", content=parsed.action, step_number=step_num, timestamp=datetime.now())
                    
                    # 执行工具（通过 ToolRegistry，不在 ReActLoop 内直接执行）
                    yield StepEvent(type="observation", content="[工具执行结果]", step_number=step_num, timestamp=datetime.now())
                    
                    self.steps.append(Step(
                        step_number=step_num,
                        thought=parsed.thought,
                        action=parsed.action,
                        observation="[工具执行结果]",
                        timestamp=datetime.now(),
                        latency_ms=0
                    ))
                
                if parsed.is_final_answer:
                    yield StepEvent(type="final", content=parsed.final_answer, step_number=step_num, timestamp=datetime.now())
                    return
        
        # 达到最大步数，强制结束
        yield StepEvent(type="error", content="达到最大步数限制", step_number=self.max_steps, timestamp=datetime.now())
```

#### 3.1.2 LLM 输出格式约定

```
系统提示词中要求 LLM 按以下格式输出：

## Thought
我需要搜索关于 MCP 协议的最新信息。MCP 是 Anthropic 推出的...

## Action
工具调用格式（JSON）：
{
  "tool": "web_search",
  "arguments": {
    "query": "MCP Model Context Protocol Anthropic 2025"
  }
}

## Observation
[工具返回的结果]
搜索结果：1. MCP (Model Context Protocol) 是 Anthropic 于 2024 年 11 月推出的开放协议...

## Final Answer
当任务完成时输出：
MCP（Model Context Protocol）是 Anthropic 推出的标准化协议，旨在让 AI 模型能够...
```

#### 3.1.3 数据模型

```python
class Step(BaseModel):
    """单步执行记录"""
    step_number: int                    # 步序号
    thought: str                        # 思考内容
    action: Optional[ToolCall] = None   # 工具调用
    observation: Optional[str] = None   # 观察结果
    timestamp: datetime                 # 执行时间
    latency_ms: int                     # 耗时(ms)

class ToolCall(BaseModel):
    """工具调用"""
    tool_name: str                      # 工具名
    arguments: dict                     # 参数
    tool_call_id: str                   # 调用ID

class ExecutionResult(BaseModel):
    """执行结果"""
    answer: str                         # 最终答案
    steps: List[Step]                   # 完整执行链
    total_steps: int                    # 总步数
    total_latency_ms: int               # 总耗时
    truncated: bool = False             # 是否被截断
    
class StepEvent(BaseModel):
    """流式事件（用于 SSE 推送）"""
    type: Literal["thought", "action", "observation", "final", "error"]
    content: str
    step_number: Optional[int] = None
    timestamp: datetime
```

---

### 3.2 Plan-and-Solve（P0 - 必做）

#### 3.2.1 两阶段架构

```python
class Planner:
    """
    Planner 规划器
    
    Phase 1: Planning（规划）
    - 分析任务复杂度
    - 拆解为子任务列表（DAG 有向无环图）
    - 为每个子任务分配最适合的 Agent
    
    Phase 2: Execution（执行）
    - Orchestrator 按依赖顺序调度
    - 支持并行执行无依赖的子任务
    - 动态调整计划（如某步失败时重新规划）
    """

class Plan(BaseModel):
    """执行计划"""
    task_id: str
    original_task: str                    # 原始任务描述
    complexity_score: float               # 复杂度评分 (0-1)
    subtasks: List[SubTask]               # 子任务列表
    estimated_steps: int                  # 预估总步数
    required_agents: List[str]            # 需要的 Agent 类型
    
class SubTask(BaseModel):
    """子任务"""
    id: str                               # 子任务ID
    description: str                      # 任务描述
    assigned_agent: str                   # 分配到的 Agent 角色
    dependencies: List[str]               # 依赖的子任务ID（空列表表示无依赖）
    status: TaskStatus = TaskStatus.PENDING
    estimated_complexity: float           # 复杂度
    
class TaskStatus(str, Enum):
    PENDING = "pending"
    WAITING = "waiting"      # 等待依赖完成
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
```

#### 3.2.2 规划 Agent 的提示词模板

```
你是一位专业的任务规划师。你的职责是将复杂任务拆解为可执行的子任务。

## 规划原则
1. 每个子任务应该是原子性的（不可再分）
2. 明确子任务间的依赖关系
3. 根据任务性质分配合适的 Agent 角色
4. 预估每个子任务的复杂度

## 可选 Agent 角色
- planner: 规划师（你本人）
- researcher: 研究员（擅长信息搜索和资料整理）
- coder: 程序员（擅长编写和执行代码）
- writer: 撰写员（擅长整合信息并撰写报告）
- reviewer: 审查员（擅长检查结果质量）
- executor: 执行员（擅长调用工具完成具体操作）

## 输出格式
请严格按以下 JSON 格式输出计划：
{
  "complexity_score": 0.7,
  "subtasks": [
    {
      "id": "task_1",
      "description": "搜索 MCP 协议的定义和背景",
      "assigned_agent": "researcher",
      "dependencies": [],
      "estimated_complexity": 0.3
    },
    {
      "id": "task_2", 
      "description": "编写 Python 函数实现 MCP 客户端",
      "assigned_agent": "coder",
      "dependencies": ["task_1"],
      "estimated_complexity": 0.6
    }
  ],
  "reasoning": "解释你的规划思路..."
}
```

---

### 3.3 Reflection（P1 - 必做）

#### 3.3.1 反思引擎

```python
class ReflectionEngine:
    """
    反思引擎：Agent 完成任务后的自我评估
    
    三个层次的反思：
    1. 步骤级反思：每步执行后即时评估
    2. 任务级反思：整个任务完成后总结
    3. 长期反思：跨任务的经验积累
    """
    
    async def reflect(self, execution_result: ExecutionResult) -> ReflectionReport:
        """任务级反思"""
        reflection_prompt = f"""
        请回顾以下任务执行过程，进行全面的自我评估：
        
        ## 原始任务
        {execution_result.original_task}
        
        ## 执行过程（共 {execution_result.total_steps} 步）
        {self._format_steps(execution_result.steps)}
        
        ## 评估维度
        1. 执行效率：是否用最少的步骤完成了任务？
        2. 决策质量：每个 Action 的选择是否合理？
        3. 错误处理：是否遇到了问题？如何解决的？
        4. 输出质量：最终结果是否完整、准确？
        5. 可优化点：如果重新执行，哪些地方可以改进？
        
        ## 输出格式
        {{
          "overall_score": 8.5,  // 0-10 分
          "efficiency_score": 8.0,
          "decision_score": 9.0,
          "error_handling_score": 8.0,
          "output_quality_score": 9.0,
          "strengths": ["优点1", "优点2"],
          "weaknesses": ["不足1", "不足2"],
          "improvement_suggestions": ["建议1", "建议2"],
          "lessons_learned": "这次任务的宝贵经验..."
        }}
        """
        
        response = await self.llm.chat(reflection_prompt)
        return ReflectionReport.parse(response)

class ReflectionReport(BaseModel):
    """反思报告"""
    overall_score: float                  # 综合评分 0-10
    efficiency_score: float               # 效率评分
    decision_score: float                 # 决策评分
    error_handling_score: float           # 错误处理评分
    output_quality_score: float           # 输出质量评分
    strengths: List[str]                  # 做得好的地方
    weaknesses: List[str]                 # 不足之处
    improvement_suggestions: List[str]    # 改进建议
    lessons_learned: str                  # 经验总结
    timestamp: datetime
```

---

### 3.4 多智能体协作（P0 - 核心）

#### 3.4.1 Agent 角色定义

| 角色 | 职责 | 专用工具 | 适用场景 |
|------|------|----------|----------|
| **PlannerAgent** | 任务分析、拆解、规划 | 无（纯规划） | 所有复杂任务的起点 |
| **ResearcherAgent** | 信息搜索、数据收集、资料整理 | WebSearch, Browser | 调研、信息收集类任务 |
| **CoderAgent** | 代码编写、调试、执行 | CodeExecutor, Calculator | 编程、数据处理类任务 |
| **WriterAgent** | 内容整合、报告撰写、文案创作 | 无（纯写作） | 写作、总结类任务 |
| **ReviewerAgent** | 质量检查、代码审查、事实核查 | 无（纯审查） | 关键输出前的质量把关 |
| **ExecutorAgent** | 工具执行、API 调用、文件操作 | 全部工具 | 需要灵活工具调用的场景 |

#### 3.4.2 Agent 基类

```python
class BaseAgent(ABC):
    """
    Agent 基类
    
    设计原则：
    - 每个 Agent 都有独立的系统提示词
    - 每个 Agent 有自己的工具集
    - Agent 通过 ReAct 循环执行任务
    - Agent 可以发送/接收消息（A2A 风格）
    - Agent 执行后有 Reflection 环节
    """
    
    # 子类必须实现的属性
    name: str
    role: str
    system_prompt: str
    available_tools: List[str]
    
    def __init__(self,
                 llm: LLMClient,
                 tool_registry: ToolRegistry,
                 memory: MemoryManager,
                 a2a_bus: A2ABus):
        self.llm = llm
        self.tool_registry = tool_registry
        self.memory = memory
        self.a2a_bus = a2a_bus
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
    async def execute(self, task: str, context: Optional[dict] = None) -> ExecutionResult:
        """执行任务（模板方法模式）"""
        # 1. 从记忆检索相关经验
        relevant_memories = await self.memory.search(task, top_k=3)
        
        # 2. 构建上下文
        execution_context = {
            "task": task,
            "memories": relevant_memories,
            **(context or {})
        }
        
        # 3. 从 MCP 获取工具 Schema 列表
        tool_schemas = self.tool_registry.discover()
        my_tools = [t for t in tool_schemas if t.name in self.available_tools]
        
        # 4. 创建 ReActLoop 并运行
        react = ReActLoop(
            agent_name=self.name,
            system_prompt=self.system_prompt,
            tools=my_tools,
            llm=self.llm
        )
        events = []
        final_answer = ""
        async for event in react.run(task, execution_context):
            events.append(event)
            if event.type == "final":
                final_answer = event.content
        
        # 5. 构建 ExecutionResult
        result = ExecutionResult(
            answer=final_answer,
            steps=[],  # 从 events 解析
            total_steps=len([e for e in events if e.type == "thought"]),
            total_latency_ms=0
        )
        
        # 6. 执行 Reflection
        result.reflection = await self._reflect(result)
        
        # 7. 存储到记忆
        await self.memory.store(task, result)
        
        return result
    
    async def receive_message(self, message: AgentMessage):
        """接收来自其他 Agent 的消息（A2A 风格）"""
        await self.message_queue.put(message)
        
    async def send_message(self, target: str, content: str, message_type: str = "task"):
        """向其他 Agent 发送消息（A2A 风格）"""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            sender=self.name,
            target=target,
            content=content,
            type=message_type,
            timestamp=datetime.now()
        )
        await self.a2a_bus.send(message)

class AgentMessage(BaseModel):
    """Agent 间消息（A2A 风格）"""
    id: str
    sender: str                           # 发送者
    target: str                           # 接收者
    content: str                          # 消息内容
    type: Literal["task", "result", "query", "feedback", "handoff"]  # 消息类型
    timestamp: datetime
    metadata: dict = {}                   # 额外元数据
```

#### 3.4.3 Orchestrator 调度器

```python
class Orchestrator:
    """
    多 Agent 调度器
    
    核心职责：
    1. 接收 Plan，构建依赖图
    2. 按拓扑排序调度子任务
    3. 管理 Agent 生命周期（创建、复用、销毁）
    4. 处理 Agent 间通信
    5. 监控执行状态，处理异常
    """
    
    async def execute_plan(self, plan: Plan, task_id: str) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        执行计划，生成流式事件
        
        调度策略：
        - 无依赖的子任务并行执行
        - 有依赖的子任务按拓扑顺序执行
        - 失败的子任务触发重试或重新规划
        """
        # 构建依赖图
        dag = self._build_dag(plan.subtasks)
        
        # 拓扑排序获取执行顺序
        execution_order = dag.topological_sort()
        
        # 按波次执行（同一波次的任务并行）
        for wave in execution_order.waves:
            # 并行执行当前波次的所有子任务
            tasks = [self._execute_subtask(st, task_id) for st in wave]
            
            for completed_task in asyncio.as_completed(tasks):
                result = await completed_task
                
                if result.status == "completed":
                    yield OrchestratorEvent(type="subtask_completed", data=result)
                elif result.status == "failed":
                    # 尝试重试或重新规划
                    retry_result = await self._handle_failure(result, dag)
                    yield OrchestratorEvent(type="subtask_retried", data=retry_result)
        
        # 所有子任务完成，生成最终结果
        yield OrchestratorEvent(type="plan_completed", data=self._aggregate_results(task_id))
    
    async def _execute_subtask(self, subtask: SubTask, task_id: str) -> SubTaskResult:
        """执行单个子任务"""
        # 获取或创建对应类型的 Agent
        agent = self.agent_pool.get_or_create(subtask.assigned_agent)
        
        # 准备上下文（包含依赖任务的结果）
        context = await self._gather_dependencies(subtask)
        
        # 执行
        result = await agent.execute(subtask.description, context)
        
        return SubTaskResult(
            subtask_id=subtask.id,
            agent=agent.name,
            result=result.answer,
            steps=result.steps,
            reflection=result.reflection,
            status="completed",
            latency_ms=result.total_latency_ms
        )
```

---

### 3.5 MCP（Model Context Protocol）（P1 - 必做）

#### 3.5.1 设计思路

不实现完整的 MCP 协议（那是一个非常复杂的服务器-客户端体系），而是**提取 MCP 的核心设计理念**，在项目中展示你对这个协议的理解：

1. **工具即服务**：每个工具都是独立的"服务"，有统一的接口描述
2. **自动发现**：Agent 不需要硬编码工具列表，可以动态发现可用工具
3. **统一调用**：所有工具通过相同的接口调用，参数自动校验
4. **Schema 驱动**：每个工具都有 JSON Schema 描述输入参数

#### 3.5.2 实现

```python
class ToolRegistry:
    """
    MCP 风格的工具注册中心
    
    模拟 MCP 的核心设计理念：
    - 工具通过装饰器注册
    - 自动生成 JSON Schema
    - 支持工具发现和动态调用
    """
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool_class: Type[Tool]) -> Type[Tool]:
        """装饰器：注册工具"""
        instance = tool_class()
        self._tools[instance.name] = instance
        logger.info(f"Registered tool: {instance.name}")
        return tool_class
    
    def discover(self) -> List[ToolSchema]:
        """
        工具发现 —— 模拟 MCP 的 tools/list 端点
        Agent 可以调用此方法来获取所有可用工具
        """
        return [tool.get_schema() for tool in self._tools.values()]
    
    async def invoke(self, tool_name: str, arguments: dict) -> ToolResult:
        """
        统一调用 —— 模拟 MCP 的 tools/call 端点
        参数自动校验
        """
        tool = self._tools.get(tool_name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found")
        
        # 参数校验（JSON Schema validation）
        tool.validate_arguments(arguments)
        
        # 执行工具
        start = time.time()
        result = await tool.execute(**arguments)
        latency = int((time.time() - start) * 1000)
        
        return ToolResult(
            content=result,
            tool_name=tool_name,
            latency_ms=latency
        )

class Tool(ABC):
    """工具基类 —— 每个工具都需要实现此接口"""
    
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    @abstractmethod
    def description(self) -> str: ...
    
    @abstractmethod
    def get_schema(self) -> ToolSchema: ...
    
    @abstractmethod
    async def execute(self, **kwargs) -> str: ...

class ToolSchema(BaseModel):
    """工具描述 Schema"""
    name: str
    description: str
    parameters: dict  # JSON Schema 格式
    required: List[str]
    returns: str      # 返回类型描述

# 使用装饰器注册工具示例
@registry.register
class WebSearchTool(Tool):
    name = "web_search"
    description = "使用 DuckDuckGo 搜索引擎查询网页信息"
    
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数",
                        "default": 5
                    }
                }
            },
            required=["query"],
            returns="搜索结果的摘要列表"
        )
    
    async def execute(self, query: str, max_results: int = 5) -> str:
        # 实际实现...
        pass
```

---

### 3.6 A2A（Agent-to-Agent Protocol）（P2 - 必做）

#### 3.6.1 设计思路

A2A 是 Google 2025 年 4 月发布的 Agent 间通信协议。同样不实现完整协议，而是**展示核心设计理念**：

1. **Agent 即对等节点**：每个 Agent 都可以发现和对等 Agent 通信
2. **任务移交（Task Handoff）**：Agent 可以将任务移交给更专业的 Agent
3. **消息传递**：标准化的消息格式，支持异步通信
4. **能力发现**：Agent 可以发布自己的能力，供其他 Agent 发现

#### 3.6.2 实现

```python
class A2ABus:
    """
    A2A 风格的消息总线（简称 A2ABus）
    
    模拟 Agent 间通信的核心机制：
    - Agent 注册和发现
    - 消息路由
    - 任务移交
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}       # 已注册 Agent
        self._capabilities: Dict[str, List[str]] = {}  # Agent -> 能力列表
        self._queues: Dict[str, asyncio.Queue] = {}    # Agent -> 消息队列
    
    def register(self, agent_id: str, capabilities: List[str], agent_ref: BaseAgent):
        """注册 Agent 及其能力"""
        self._agents[agent_id] = agent_ref
        self._capabilities[agent_id] = capabilities
        self._queues[agent_id] = asyncio.Queue()
    
    def discover(self, capability: Optional[str] = None) -> List[AgentInfo]:
        """
        发现 Agent —— 模拟 A2A 的 Agent 发现机制
        可以按能力筛选
        """
        results = []
        for name, caps in self._capabilities.items():
            if capability is None or capability in caps:
                results.append(AgentInfo(
                    name=name,
                    capabilities=caps,
                    status="available"
                ))
        return results
    
    async def send(self, message: AgentMessage) -> bool:
        """
        消息路由 —— 模拟 A2A 的消息传递
        """
        target = self._agents.get(message.target)
        if not target:
            logger.error(f"Target agent '{message.target}' not found")
            return False
        
        await target.receive_message(message)
        return True
    
    def get_queue(self, agent_id: str) -> asyncio.Queue:
        """获取 Agent 的消息队列"""
        return self._queues[agent_id]
    
    async def handoff(self, 
                      from_agent: str, 
                      to_agent: str, 
                      task: str,
                      context: dict = None) -> str:
        """
        任务移交 —— 核心 A2A 概念
        一个 Agent 将任务移交给另一个更专业的 Agent
        """
        # 发送移交消息
        handoff_msg = AgentMessage(
            sender=from_agent,
            target=to_agent,
            content=task,
            type="handoff",
            metadata={
                "original_context": context,
                "handoff_reason": f"'{from_agent}' 认为 '{to_agent}' 更适合处理此任务"
            }
        )
        
        # 路由到目标 Agent
        await self.route(handoff_msg)
        
        # 等待目标 Agent 完成
        target = self._agents[to_agent]
        result = await target.execute(task, context)
        
        return result.answer

class AgentInfo(BaseModel):
    """Agent 信息（用于发现）"""
    name: str
    capabilities: List[str]
    status: Literal["available", "busy", "offline"]
    endpoint: Optional[str] = None  # 通信端点
```

#### 3.6.3 A2A 协作流程示例

```
用户任务: "调研 2025 年 AI Agent 框架，写一篇对比文章"

协作流程:
1. PlannerAgent 拆解任务
   → [任务规划完成]

2. PlannerAgent 通过 A2A 发送消息给 ResearcherAgent:
   "请搜索 AutoGen、CrewAI、LangGraph 的最新信息"
   → ResearcherAgent 执行搜索，返回结果

3. PlannerAgent 评估 Researcher 的结果
   → 判断信息充足后，通过 A2A Handoff 移交给 WriterAgent:
   "基于以下研究结果，撰写一篇对比文章..."

4. WriterAgent 撰写文章
   → 完成后通知 PlannerAgent

5. PlannerAgent 通过 A2A 移交给 ReviewerAgent:
   "请审查这篇文章的准确性和完整性"

6. ReviewerAgent 审查并提出修改建议
   → 返回给 WriterAgent 修改

7. PlannerAgent 整合最终结果
   → 输出完整报告
```

---

### 3.7 RAG（检索增强生成）（P1 - 必做）

#### 3.7.1 简化但完整的 RAG 链路

```python
class RAGSystem:
    """
    RAG 系统：为 Agent 提供外部知识检索能力
    
    完整链路：
    1. 文档加载 & 切分
    2. 向量化 & 索引（FAISS）
    3. 查询向量化
    4. 相似度检索
    5. 结果重排序
    6. 上下文注入
    """
    
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        self.embedder = EmbeddingClient(embedding_model)
        self.vector_store = FAISSIndex(dimension=1536)
        self.documents: List[Document] = []
    
    async def add_documents(self, documents: List[Document]):
        """添加文档到知识库"""
        # 1. 切分长文档
        chunks = self._chunk_documents(documents)
        
        # 2. 向量化
        embeddings = await self.embedder.embed([c.content for c in chunks])
        
        # 3. 存入向量索引
        self.vector_store.add(embeddings, chunks)
        self.documents.extend(chunks)
    
    async def search(self, query: str, top_k: int = 5) -> List[RetrievalResult]:
        """检索相关文档"""
        # 1. 查询向量化
        query_embedding = await self.embedder.embed([query])
        
        # 2. 相似度检索
        results = self.vector_store.search(query_embedding[0], top_k=top_k * 2)
        
        # 3. 重排序（简单的交叉编码器）
        reranked = await self._rerank(query, results)
        
        return reranked[:top_k]

class Document(BaseModel):
    """文档"""
    id: str
    content: str
    metadata: dict = {}
    source: Optional[str] = None

class RetrievalResult(BaseModel):
    """检索结果"""
    document: Document
    similarity_score: float       # 相似度分数
    rerank_score: Optional[float] = None  # 重排序分数
```

#### 3.7.2 Agent 集成

```python
# Agent 在执行任务时自动使用 RAG
async def execute_with_rag(self, task: str):
    # 1. 先从知识库检索相关信息
    relevant_docs = await rag_system.search(task, top_k=3)
    
    # 2. 将检索结果注入上下文
    context = {
        "retrieved_knowledge": [
            {"content": doc.document.content, "source": doc.document.source}
            for doc in relevant_docs
        ],
        "task": task
    }
    
    # 3. 执行 ReAct 循环（带 RAG 上下文）
    result = await self.react_loop.run(task, context)
    
    return result
```

---

### 3.8 Memory（记忆系统）（P1 - 必做）

#### 3.8.1 三层记忆架构

```python
class MemoryManager:
    """
    三层记忆系统
    
    1. 短期记忆（Short-Term Memory）
       - 当前任务的对话历史
       - 存储：内存（Redis/内存字典）
       - 作用：维持当前对话的上下文连贯性
    
    2. 长期记忆（Long-Term Memory）
       - 跨任务的历史执行记录
       - 存储：SQLite + FAISS 向量检索
       - 作用：Agent 可以"回忆"之前的经验
    
    3. 经验记忆（Experience Memory）
       - Reflection 总结的经验教训
       - 存储：结构化存储
       - 作用：指导未来的决策
    """
    
    def __init__(self):
        self.short_term = ShortTermMemory()    # 当前任务上下文
        self.long_term = LongTermMemory()       # 持久化存储
        self.experience = ExperienceMemory()    # Reflection 经验
    
    async def store(self, task: str, result: ExecutionResult):
        """存储执行结果到记忆"""
        # 存入短期记忆
        self.short_term.add(result)
        
        # 存入长期记忆
        await self.long_term.store(task, result)
        
        # 如果有 Reflection，提取经验
        if result.reflection:
            await self.experience.store(result.reflection)
    
    async def search(self, query: str, top_k: int = 3) -> List[MemoryEntry]:
        """
        从记忆检索相关信息
        检索顺序：短期 → 长期 → 经验
        """
        results = []
        
        # 短期记忆（最近的相关记录）
        short_term_results = self.short_term.search(query, top_k=2)
        results.extend(short_term_results)
        
        # 长期记忆（向量检索）
        long_term_results = await self.long_term.search(query, top_k=top_k)
        results.extend(long_term_results)
        
        # 经验记忆
        experience_results = await self.experience.search(query, top_k=2)
        results.extend(experience_results)
        
        # 去重并按相关性排序
        return self._deduplicate_and_rank(results)[:top_k]

class ShortTermMemory:
    """短期记忆：当前任务的上下文窗口"""
    
    def __init__(self, max_turns: int = 20):
        self.turns: List[Turn] = []
        self.max_turns = max_turns
    
    def add(self, result: ExecutionResult):
        """添加一轮对话/执行"""
        self.turns.append(Turn(
            role="assistant",
            content=result.answer,
            steps=result.steps,
            timestamp=datetime.now()
        ))
        # 保持窗口大小
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]
    
    def get_context(self) -> str:
        """获取当前上下文的文本表示"""
        return "\n".join([f"{t.role}: {t.content}" for t in self.turns])

class LongTermMemory:
    """长期记忆：跨任务的持久化存储 + 向量检索"""
    
    async def store(self, task: str, result: ExecutionResult):
        """存储执行记录"""
        entry = MemoryEntry(
            task=task,
            answer=result.answer,
            steps_summary=self._summarize_steps(result.steps),
            reflection_score=result.reflection.overall_score if result.reflection else None,
            embedding=await self._embed(task + " " + result.answer)
        )
        await self.db.insert(entry)
    
    async def search(self, query: str, top_k: int = 3) -> List[MemoryEntry]:
        """向量检索相关历史记录"""
        query_embedding = await self._embed(query)
        return await self.vector_store.search(query_embedding, top_k)

class ExperienceMemory:
    """经验记忆：存储 Reflection 总结的经验"""
    
    async def store(self, reflection: ReflectionReport):
        """提取并存储经验教训"""
        experience = ExperienceEntry(
            lessons_learned=reflection.lessons_learned,
            improvement_suggestions=reflection.improvement_suggestions,
            avg_score=reflection.overall_score,
            timestamp=datetime.now()
        )
        await self.db.insert(experience)
    
    async def search(self, query: str, top_k: int = 2) -> List[ExperienceEntry]:
        """检索相关经验"""
        # 关键词匹配 + 分数排序
        return await self.db.search_by_keywords(query, top_k)

class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str
    task: str
    answer: str
    steps_summary: str
    reflection_score: Optional[float]
    embedding: Optional[List[float]]
    timestamp: datetime

class ExperienceEntry(BaseModel):
    """经验条目"""
    id: str
    lessons_learned: str
    improvement_suggestions: List[str]
    avg_score: float
    timestamp: datetime
```

---

## 4. 前端设计

### 4.1 页面结构

```
Dashboard (主控制台)
├── 顶部导航栏
│   ├── Logo + 项目名称
│   ├── 当前模型显示 (Kimi / DeepSeek)
│   └── 状态指示器 (系统状态)
│
├── 左侧边栏 (25% 宽度)
│   ├── 新建任务按钮
│   ├── 历史任务列表
│   │   └── 任务卡片 (标题/状态/时间)
│   └── 系统设置入口
│
└── 主内容区 (75% 宽度)
    ├── 任务输入区 (顶部)
    │   ├── 文本输入框
    │   ├── 预设场景选择
    │   └── 执行按钮
    │
    ├── 执行监控区 (核心区域)
    │   ├── Tab 1: 执行计划 (Plan)
    │   │   └── 子任务列表 + 依赖图
    │   ├── Tab 2: Agent 监控 (核心)
    │   │   ├── Agent 卡片列表 (每个 Agent 一个卡片)
    │   │   └── ReAct 流：Thought → Action → Observation
    │   ├── Tab 3: 协作流程图
    │   │   └── ReactFlow 节点图 (Agent 间消息传递)
    │   ├── Tab 4: 工具日志
    │   │   └── 时间线形式的工具调用记录
    │   ├── Tab 5: 记忆检索
    │   │   └── 检索结果 + 相似度分数
    │   └── Tab 6: 反思报告
    │       └── Reflection 评分 + 建议
    │
    └── 结果展示区 (底部)
        ├── 最终输出 (Markdown 渲染)
        └── 导出按钮
```

### 4.2 核心组件

#### AgentMonitor 组件（最重要）

```typescript
// Agent 实时监控面板
interface AgentMonitorProps {
  agents: AgentExecution[];      // 各 Agent 的执行状态
  currentStep: StepEvent | null; // 当前步骤
  isRunning: boolean;
}

// 功能：
// 1. 显示每个 Agent 的当前状态 (等待中/执行中/已完成)
// 2. 实时展示 ReAct 循环的三个阶段 (Thought/Action/Observation)
// 3. 打字机效果显示流式输出
// 4. 步骤计数器 + 耗时显示
// 5. 工具调用时高亮显示
```

#### CollaborationGraph 组件

```typescript
// 协作流程图 (ReactFlow)
interface CollaborationGraphProps {
  agents: AgentNode[];
  messages: AgentMessage[];      // Agent 间消息
  activePath: string[];          // 当前激活的路径
}

// 功能：
// 1. 节点 = Agent 角色 (不同颜色区分)
// 2. 边 = 消息/任务传递
// 3. 动画效果显示消息流动
// 4. 点击节点查看详情
```

---

## 5. API 接口设计

### 5.1 核心接口

| 方法 | 路径 | 说明 | SSE? |
|------|------|------|------|
| POST | /api/tasks | 创建任务 | 否 |
| GET | /api/tasks/{id} | 获取任务详情 | 否 |
| GET | /api/tasks/{id}/stream | 流式执行（核心） | ✅ |
| GET | /api/tasks/{id}/plan | 获取执行计划 | 否 |
| GET | /api/tasks/{id}/result | 获取最终结果 | 否 |
| GET | /api/tasks/{id}/reflect | 获取反思报告 | 否 |
| GET | /api/tools | 列出可用工具 (MCP 发现) | 否 |
| POST | /api/agents/{id}/message | Agent 间通信 (A2A) | 否 |
| POST | /api/memory/search | 记忆检索 (RAG) | 否 |

### 5.2 SSE 事件类型

```typescript
// SSE 事件流 (按时间顺序)
type SSEEvent =
  | { type: "plan_created"; data: Plan }           // 计划已创建
  | { type: "agent_started"; data: { agent: string; subtask: string } }
  | { type: "thought"; data: { agent: string; content: string; step: number } }
  | { type: "action"; data: { agent: string; tool: string; args: object } }
  | { type: "observation"; data: { agent: string; result: string } }
  | { type: "agent_completed"; data: { agent: string; result: string } }
  | { type: "reflection"; data: ReflectionReport }
  | { type: "final_result"; data: string }
  | { type: "error"; data: { message: string; agent?: string } };
```

---

## 6. 数据库设计

### 6.1 SQLite 表结构

```sql
-- 任务表
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    original_task TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending','planning','running','completed','failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    total_agents INTEGER DEFAULT 0,
    total_steps INTEGER DEFAULT 0,
    total_latency_ms INTEGER
);

-- 子任务表
CREATE TABLE subtasks (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id),
    description TEXT NOT NULL,
    assigned_agent TEXT NOT NULL,
    dependencies TEXT, -- JSON 数组
    status TEXT CHECK(status IN ('pending','waiting','running','completed','failed')),
    result TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    latency_ms INTEGER
);

-- Agent 执行记录表
CREATE TABLE agent_executions (
    id TEXT PRIMARY KEY,
    task_id TEXT REFERENCES tasks(id),
    agent_name TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    subtask_id TEXT REFERENCES subtasks(id),
    steps_json TEXT, -- JSON 格式的步骤记录
    result TEXT,
    reflection_json TEXT, -- JSON 格式的反思报告
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 记忆表（长期记忆）
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    task TEXT NOT NULL,
    answer TEXT,
    steps_summary TEXT,
    reflection_score REAL,
    embedding_json TEXT, -- JSON 格式的向量
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 经验表
CREATE TABLE experiences (
    id TEXT PRIMARY KEY,
    lessons_learned TEXT,
    improvement_suggestions TEXT, -- JSON 数组
    avg_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 7. 预设 Demo 场景

### 7.1 场景 1：调研分析

**用户输入**："调研 2025 年 AI Agent 领域的主流框架，对比 AutoGen、CrewAI、LangGraph 的优缺点，给出选型建议"

**执行流程**：
```
Planner → 拆解为 6 个子任务
├── Researcher → 搜索 AutoGen 信息
├── Researcher → 搜索 CrewAI 信息
├── Researcher → 搜索 LangGraph 信息
├── Researcher → 搜索 2025 年 Agent 趋势 (并行执行)
├── Writer → 整合对比分析 (依赖前 4 个)
└── Reviewer → 审查准确性 (依赖 Writer)
```

### 7.2 场景 2：编程任务

**用户输入**："写一个 Python 函数，输入一个 URL，返回网页中所有图片链接，要求处理相对路径"

**执行流程**：
```
Planner → 拆解为 4 个子任务
├── Researcher → 搜索最佳实践
├── Coder → 编写代码
├── Executor → 执行测试
└── Reviewer → 代码审查
```

### 7.3 场景 3：内容创作

**用户输入**："帮我写一篇关于 MCP 协议的技术博客，要求通俗易懂，适合初学者"

**执行流程**：
```
Planner → 拆解为 5 个子任务
├── Researcher → 搜索 MCP 资料
├── Researcher → 搜索类比和案例
├── Writer → 撰写博客
├── Reviewer → 审查质量
└── Writer → 修改定稿
```

### 7.4 场景 4：数据分析

**用户输入**："分析这个 CSV 文件的销售数据，找出趋势并可视化"

**执行流程**：
```
Planner → 拆解为 5 个子任务
├── Coder → 加载和清洗数据
├── Coder → 数据分析
├── Coder → 生成可视化图表
├── Writer → 撰写分析报告
└── Reviewer → 验证结论
```

---

## 8. 面试加分项清单

### 8.1 代码层面

- [ ] **类型安全**：Python 和 TypeScript 都使用完整的类型注解
- [ ] **错误处理**：LLM 调用失败重试、工具超时处理、降级策略
- [ ] **流式输出**：SSE 实时推送 Agent 思维过程
- [ ] **可扩展性**：新增 Agent 角色只需继承基类
- [ ] **多模型支持**：切换 Kimi / DeepSeek 只需改配置
- [ ] **日志系统**：结构化日志，方便调试

### 8.2 文档层面

- [ ] **README**：项目介绍、架构图、安装步骤、Demo 截图
- [ ] **ARCHITECTURE**：技术决策、数据流图、模块说明
- [ ] **API 文档**：FastAPI 自动生成的 OpenAPI (Swagger)
- [ ] **代码注释**：核心逻辑有详细注释

### 8.3 展示层面

- [ ] **Web Demo**：可在线体验
- [ ] **Docker**：一键启动
- [ ] **GitHub Actions**：CI/CD 流水线

---

## 9. 技术风险与应对

| 风险 | 概率 | 应对方案 |
|------|------|----------|
| LLM API 调用超时/失败 | 高 | 重试机制（指数退避）+ 降级到备用模型 |
| LLM 输出格式不符合预期 | 高 | 严格的解析逻辑 + 异常时重新生成 |
| 代码执行工具安全风险 | 中 | 沙箱化（Docker / 限制系统调用） |
| 前端 SSE 连接断开 | 中 | 自动重连 + 状态恢复 |
| 向量库性能问题 | 低 | FAISS 足够支撑万级文档 |
| 多 Agent 调度死锁 | 低 | 依赖图检测环 + 超时强制释放 |

---

## 10. 成功标准

### 10.1 功能标准

- [ ] 三个 Demo 场景能稳定跑通（调研/编程/写作）
- [ ] ReAct 过程可视化完整（Thought → Action → Observation）
- [ ] 多 Agent 协作流程图正确显示
- [ ] MCP 工具注册和发现可演示
- [ ] A2A Agent 间通信可演示
- [ ] RAG 记忆检索可演示
- [ ] Reflection 反思报告可查看

### 10.2 技术标准

- [ ] 代码覆盖 8 个核心方向
- [ ] 类型注解完整（Python + TypeScript）
- [ ] 有错误处理和重试机制
- [ ] SSE 流式输出稳定
- [ ] Docker 一键启动成功
- [ ] Web Demo 可在线访问

### 10.3 面试标准

- [ ] 面试官能在 5 分钟内理解项目
- [ ] 能在 10 分钟内完整演示一个场景
- [ ] 能清晰解释每个核心方向的设计思路
- [ ] 能展示代码层面的工程能力

---

> **文档版本**：v1.0  
> **创建日期**：2025-01-15  
> **更新记录**：初始版本，覆盖全部 8 个核心方向
