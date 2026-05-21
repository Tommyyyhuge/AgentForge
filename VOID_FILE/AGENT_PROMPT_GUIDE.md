# OpenCode CLI Prompt 写作指南
> **目标**：教你如何把 PRD 中的任务翻译成 AI Agent（OpenCode CLI / Claude Code）能一次性高质量完成的 Prompt

---

## 1. 核心原则：任务拆解粒度

### ❌ 太大的任务（AI 会翻车）

```
"帮我实现整个后端"
"写一个 Agent 调度系统"
"把前端所有组件都写了"
```

**为什么不行**：AI 会遗漏细节、生成不符合架构的代码、难以调试。

### ❌ 太小的任务（效率低）

```
"帮我 import 一下 os 模块"
"在这个函数里加一行 print"
```

**为什么不行**：你来回对话的时间比手写还长。

### ✅ 刚好的任务（一个文件 or 一个类）

```
"创建一个 Pydantic 模型文件，定义 Task、SubTask、AgentStep 三个模型"
"实现 ReActLoop 类，包含完整的推理循环逻辑"
"创建一个 React 组件 AgentMonitor，展示 Agent 实时执行状态"
```

**判断标准**：
- 输出大约是 **1-3 个文件**
- 能在 **1 次 AI 回复** 中完整交付
- 人类审查大约需要 **10-20 分钟**

---

## 2. Prompt 万能模板

每个 Prompt 都按这个结构写，AI 输出质量会稳定很多：

```
## 任务概述
【一句话说明要做什么】

## 文件位置
【新建 or 修改哪个文件】
文件路径: `backend/agent_forge/core/react_loop.py`

## 上下文信息
【AI 需要知道的相关代码/架构信息】
- 相关模型定义在 `backend/agent_forge/models/schemas.py`
- 工具基类在 `backend/agent_forge/tools/base.py`
- LLM 客户端在 `backend/agent_forge/core/llm_client.py`

## 详细需求
【具体要实现什么，尽量详细】
1. 实现 ReAct 推理循环
2. 每轮循环执行：构建提示词 → 调用 LLM → 解析输出 → 执行工具 → 获取观察
3. 最大步数限制 10 步
4. 支持流式输出（yield 事件）
5. 达到最大步数时强制结束并返回已收集的结果

## 接口定义
【输入输出要明确】
class ReActLoop:
    def __init__(self, agent, tools: List[Tool], max_steps: int = 10)
    async def run(self, task: str, context: dict = None) -> AsyncGenerator[StepEvent, None]

class StepEvent(BaseModel):
    type: Literal["thought", "action", "observation", "final", "error"]
    content: str
    step_number: int
    timestamp: datetime

## 依赖关系
【需要引用哪些已有代码】
- 依赖: backend/agent_forge/models/schemas.py (Task, ToolCall 等模型)
- 依赖: backend/agent_forge/tools/base.py (Tool 基类)
- 被依赖: backend/agent_forge/agents/base.py (Agent 基类会调用 ReActLoop)

## 验收标准
【怎么算完成】
- [ ] 代码能通过 Python 语法检查
- [ ] 能正确解析 LLM 输出的 Thought/Action/Observation
- [ ] 工具调用失败时有错误处理
- [ ] 达到 max_steps 时强制结束
- [ ] 有完整的类型注解

## 注意事项
【AI 容易出错的地方，提前提醒】
- 解析 LLM 输出时用正则表达式，不要假设格式完美
- 工具调用的参数要校验后再执行
- 所有异步方法都要用 async/await
- 用 logger 代替 print 输出调试信息
```

---

## 3. 按 Sprint 的 Prompt 示例

### Sprint 1 示例

#### Prompt 1: 数据模型定义

```
## 任务概述
定义 AgentForge 的核心数据模型

## 文件位置
新建: `backend/agent_forge/models/schemas.py`

## 上下文信息
这是 AgentForge 多智能体协作平台的数据模型层。所有后续模块都会引用这些模型。
项目使用 Pydantic v2 进行数据校验。

## 详细需求
定义以下模型（都要继承 BaseModel）：

1. Task - 主任务
   - id: str, original_task: str, status: TaskStatus(枚举)
   - created_at, completed_at: datetime
   - total_agents, total_steps, total_latency_ms: int

2. SubTask - 子任务
   - id: str, task_id: str, description: str, assigned_agent: str
   - dependencies: List[str] (依赖的其他子任务ID)
   - status: TaskStatus, result: Optional[str]
   - started_at, completed_at: Optional[datetime], latency_ms: int

3. Step - ReAct 单步
   - step_number: int, thought: str
   - action: Optional[ToolCall], observation: Optional[str]
   - timestamp: datetime, latency_ms: int

4. ToolCall - 工具调用
   - tool_name: str, arguments: dict, tool_call_id: str

5. ExecutionResult - 执行结果
   - answer: str, steps: List[Step], total_steps: int
   - total_latency_ms: int, truncated: bool = False

6. StepEvent - SSE 流式事件
   - type: Literal["thought","action","observation","final","error"]
   - content: str, step_number: Optional[int], timestamp: datetime

7. ReflectionReport - 反思报告
   - overall_score: float (0-10), strengths: List[str], weaknesses: List[str]
   - improvement_suggestions: List[str], lessons_learned: str
   - 以及各维度评分: efficiency_score, decision_score, error_handling_score, output_quality_score

8. AgentMessage - Agent 间消息 (A2A 风格)
   - id: str, sender: str, target: str, content: str
   - type: Literal["task","result","query","feedback","handoff"]
   - timestamp: datetime, metadata: dict = {}

9. Plan - 执行计划
   - task_id: str, original_task: str, complexity_score: float (0-1)
   - subtasks: List[SubTask], estimated_steps: int, required_agents: List[str]

10. enums: TaskStatus (pending/waiting/running/completed/failed/retrying)

## 验收标准
- [ ] 所有模型都有完整的类型注解
- [ ] 有 Config 配置使用 from_attributes
- [ ] 枚举值用 StrEnum
- [ ] 能通过 Python 语法检查
```

#### Prompt 2: Agent 基类

```
## 任务概述
实现 Agent 基类，所有具体 Agent 角色都继承此类

## 文件位置
新建: `backend/agent_forge/agents/base.py`

## 上下文信息
- 数据模型: `backend/agent_forge/models/schemas.py` (Step, ExecutionResult, ReflectionReport, AgentMessage 等)
- ReAct 循环: 将在 `backend/agent_forge/core/react_loop.py` 中实现
- 记忆系统: `backend/agent_forge/core/memory.py`
- 工具基类: `backend/agent_forge/tools/base.py`
- LLM 客户端: `backend/agent_forge/core/llm_client.py` (假设已有，封装了 OpenAI 兼容接口)

## 详细需求
实现 BaseAgent 抽象基类（模板方法模式）：

1. 子类必须实现的类属性:
   - name: str (Agent 名称，如 "researcher")
   - role: str (角色描述)
   - system_prompt: str (系统提示词)
   - available_tools: List[str] (可用工具名列表，如 ["web_search", "browser"])

2. __init__ 注入的依赖:
   - llm: LLMClient (LLM 客户端实例)
   - tool_registry: ToolRegistry (MCP 工具注册中心)
   - memory: MemoryManager (记忆管理器)
   - a2a_bus: A2ABus (A2A 消息总线)

3. 核心方法:
   - async execute(task: str, context: Optional[dict] = None) -> ExecutionResult:
     * 从记忆检索相关经验 → 构建上下文
     * 从 tool_registry 获取可用工具 Schema
     * 创建 ReActLoop 并运行（流式收集事件）
     * 执行 Reflection → 存储到记忆 → 返回结果
   - async send_message(target: str, content: str, msg_type: str): 通过 a2a_bus 发送
   - async receive_message(message: AgentMessage): 接收消息入队
   - async _reflect(result: ExecutionResult) -> Optional[ReflectionReport]: 内部反思

4. 设计要点:
   - execute 是模板方法，子类一般不覆盖
   - name/role/system_prompt/available_tools 由子类定义，不在 __init__ 传参
   - 用 async/await，所有 IO 操作都是异步的
   - 是抽象类(ABC)，不能直接实例化

## 接口定义
class BaseAgent(ABC):
    # 子类必须实现的类属性
    name: str
    role: str
    system_prompt: str
    available_tools: List[str]
    
    def __init__(self, llm: LLMClient, tool_registry: ToolRegistry, memory: MemoryManager, a2a_bus: A2ABus)
    async def execute(self, task, context) -> ExecutionResult
    async def send_message(self, target, content, message_type)
    async def receive_message(self, message)
    async def _reflect(self, result) -> Optional[ReflectionReport]

## 验收标准
- [ ] 正确的抽象基类设计
- [ ] execute 方法编排完整流程
- [ ] 所有异步方法正确使用 async/await
- [ ] 有完整的类型注解和 docstring
- [ ] 错误处理：LLM 调用失败时抛出可捕获的异常
```

#### Prompt 3: ReAct 引擎

```
## 任务概述
实现完整的 ReAct 推理循环引擎

## 文件位置
新建: `backend/agent_forge/core/react_loop.py`

## 上下文信息
- 数据模型: `backend/agent_forge/models/schemas.py` (Step, ToolCall, ExecutionResult, StepEvent)
- 工具基类: `backend/agent_forge/tools/base.py` (Tool 基类)
- Agent 基类: `backend/agent_forge/agents/base.py` (BaseAgent)

## 详细需求
实现 ReActLoop 类：

1. 初始化:
   - __init__(self, agent_name: str, system_prompt: str, tools: List[ToolSchema], llm: LLMClient, max_steps: int = 10)
   - 参数说明：
     * agent_name: Agent 名称（用于日志和事件标识）
     * system_prompt: Agent 的系统提示词
     * tools: 可用工具的 Schema 列表（从 MCP ToolRegistry.discover() 获取）
     * llm: LLMClient 实例
     * max_steps: 最大步数限制（默认 10）

2. 核心方法:
   - async run(self, task: str, context: Optional[str] = None) -> AsyncGenerator[StepEvent, None]
   - 返回 AsyncGenerator，流式 yield StepEvent
   - 每轮循环：
     a. 构建 prompt（system_prompt + 任务 + 工具描述 + 历史步骤）
     b. 调用 LLM（流式，通过 self.llm.chat）
     c. 流式解析响应，提取 Thought
     d. 提取 Action（工具调用 JSON）
     e. yield action 事件（工具执行由调用方通过 ToolRegistry 完成）
     f. 获取 Observation 后继续
     g. 判断是否 Final Answer → yield final 事件并 return

3. Prompt 模板设计:
   LLM 被要求按以下格式输出：
   ```
   ## Thought
   [思考过程]
   
   ## Action
   {"tool": "tool_name", "arguments": {...}}
   
   ## Observation
   [工具返回结果，由系统填充]
   
   ## Final Answer
   [最终答案]
   ```

4. 解析逻辑:
   - 用正则表达式解析各个部分（Thought/Action/Observation/Final Answer）
   - Action 必须是合法 JSON，包含 tool 和 arguments 字段
   - 解析失败时 yield error 事件，连续 3 次失败则终止

5. 终止条件:
   - 输出 Final Answer → yield final 事件 → return
   - 达到 max_steps → yield error 事件 → return
   - 连续 3 次解析失败 → yield error 事件 → return
   
6. 设计要点:
   - ReActLoop 不直接执行工具，只 yield action 事件
   - 工具执行由调用方（BaseAgent）通过 ToolRegistry.invoke() 完成
   - 所有事件都包含 step_number 和 timestamp

## 验收标准
- [ ] 能正确解析 Thought/Action/Observation/Final Answer
- [ ] 工具调用参数正确传递
- [ ] 流式 yield StepEvent
- [ ] 达到 max_steps 时优雅结束
- [ ] 有完整的错误处理和重试
- [ ] 类型注解完整

## 注意事项
- 解析 LLM 输出要用 try/except，不要假设格式完美
- 工具不存在时要 yield error 事件
- 所有时间戳用 UTC
```

### Sprint 2 示例

#### Prompt 4: 调度器 Orchestrator

```
## 任务概述
实现多 Agent 调度器，按依赖图调度子任务执行

## 文件位置
新建: `backend/agent_forge/core/orchestrator.py`

## 上下文信息
- Plan/SubTask 模型: `backend/agent_forge/models/schemas.py`
- Agent 基类: `backend/agent_forge/agents/base.py` (BaseAgent)
- 各 Agent 实现: `backend/agent_forge/agents/` 目录下
  - planner_agent.py
  - researcher_agent.py
  - coder_agent.py
  - writer_agent.py

## 详细需求
实现 Orchestrator 类：

1. 属性:
   - agent_pool: Dict[str, BaseAgent] (已创建的 Agent 实例)
   - task_results: Dict[str, SubTaskResult] (子任务执行结果)

2. 核心方法:
   - async execute_plan(self, plan: Plan, task_id: str) -> AsyncGenerator[OrchestratorEvent, None]:
     a. 构建 DAG 依赖图
     b. 拓扑排序获取执行波次
     c. 同波次并行执行
     d. yield 各种事件 (subtask_started, subtask_completed, agent_started 等)
     e. 失败时触发重试或重新规划

   - async _execute_subtask(self, subtask: SubTask, task_id: str) -> SubTaskResult:
     a. 从 agent_pool 获取对应类型的 Agent
     b. 收集依赖任务的执行结果作为上下文
     c. 调用 agent.execute()
     d. 返回 SubTaskResult

   - _build_dag(self, subtasks: List[SubTask]) -> DAG:
     构建有向无环图，检测环

   - _handle_failure(self, failed: SubTaskResult, dag: DAG) -> SubTaskResult:
     重试逻辑（最多2次），仍失败则标记为 failed

3. OrchestratorEvent 类型:
   - plan_started, subtask_started, subtask_completed, subtask_failed
   - agent_started, agent_completed, agent_failed
   - plan_completed, plan_failed

## 验收标准
- [ ] 能按依赖顺序正确调度
- [ ] 无依赖的子任务并行执行
- [ ] 失败时有重试机制
- [ ] 有完整的流式事件输出
- [ ] DAG 环检测
```

### Sprint 3 示例

#### Prompt 5: MCP 工具注册中心

```
## 任务概述
实现 MCP 风格的工具注册和发现机制

## 文件位置
新建: `backend/agent_forge/mcp/tool_registry.py`

## 上下文信息
- 工具基类: `backend/agent_forge/tools/base.py`
- ToolSchema 模型: `backend/agent_forge/models/schemas.py`

## 详细需求
实现 ToolRegistry 单例：

1. 核心方法:
   - register(self, tool_class) -> tool_class: 装饰器注册工具
   - discover(self) -> List[ToolSchema]: 返回所有可用工具的描述
   - invoke(self, tool_name: str, arguments: dict) -> ToolResult: 统一调用

2. 工具基类 Tool:
   - 抽象属性: name, description
   - 抽象方法: get_schema() -> ToolSchema, execute(**kwargs) -> str

3. 内置工具（一起实现）:
   - WebSearchTool: 用 DuckDuckGo 搜索 (需要安装 duckduckgo-search)
   - CalculatorTool: 安全计算数学表达式
   - CodeExecutorTool: 在子进程中执行 Python 代码（带超时和安全限制）
   - BrowserTool: 抓取网页内容 (用 requests + beautifulsoup)

4. 每个工具都要有完整的 JSON Schema 描述参数

## 验收标准
- [ ] 装饰器注册方式工作正常
- [ ] discover() 返回正确的工具描述
- [ ] invoke() 正确调用工具并返回结果
- [ ] 参数校验失败时返回清晰错误
- [ ] 内置工具都能正常工作
- [ ] CodeExecutor 有超时(30s)和 import 限制

## 注意事项
- CodeExecutor 要限制危险操作，禁止 os.system, subprocess, open 文件写等
- 用 ast 模块检查代码安全性
- 超时用 signal 或 asyncio.wait_for
```

### Sprint 4 示例

#### Prompt 6: 前端 AgentMonitor 组件

```
## 任务概述
创建 Agent 实时监控组件，展示 ReAct 执行过程

## 文件位置
新建: `frontend/src/components/AgentMonitor.tsx`

## 上下文信息
- 前端技术栈: React 18 + TypeScript + Tailwind CSS + shadcn/ui
- SSE 连接在 `frontend/src/api/taskApi.ts` 中封装
- 数据类型:
  ```typescript
  interface StepEvent {
    type: "thought" | "action" | "observation" | "final" | "error";
    content: string;
    step_number?: number;
    timestamp: string;
    agent?: string;
  }
  
  interface AgentExecution {
    name: string;
    role: string;
    status: "pending" | "running" | "completed" | "failed";
    currentStep?: number;
    totalSteps?: number;
  }
  ```

## 详细需求
实现 AgentMonitor 组件：

1. 布局：
   - 左侧：Agent 列表卡片（显示所有参与的 Agent）
   - 右侧：选中 Agent 的详细执行流

2. Agent 卡片：
   - 显示 Agent 名称、角色、当前状态
   - 状态用不同颜色：pending(灰) / running(蓝) / completed(绿) / failed(红)
   - 当前步数/总步数
   - 点击切换查看详情

3. 执行流详情：
   - 按时间倒序展示 Thought → Action → Observation
   - 不同类型用不同样式：
     * Thought: 气泡样式，左侧灰色边框
     * Action: 卡片样式，蓝色边框，显示工具名和参数
     * Observation: 卡片样式，绿色边框，可折叠
     * Final: 醒目样式，金色边框
   - 打字机效果显示流式内容
   - 代码块语法高亮

4. 交互：
   - 自动滚动到最新内容
   - 暂停/继续自动滚动
   - 复制某一步的内容

## 验收标准
- [ ] 正确显示 Agent 状态变化
- [ ] 流式内容实时更新
- [ ] Thought/Action/Observation 区分明显
- [ ] 打字机效果流畅
- [ ] 响应式布局
```

---

## 4. 给 AI 的 Prompt 写作技巧

### 4.1 必须包含的信息（按优先级）

| 优先级 | 信息 | 说明 |
|--------|------|------|
| **必须** | 文件路径 | 新建 or 修改，完整路径 |
| **必须** | 输入/输出接口 | 函数签名、类定义、参数类型 |
| **必须** | 核心逻辑描述 | 要做什么，关键步骤 |
| **强烈建议** | 依赖关系 | 引用了哪些已有代码 |
| **强烈建议** | 验收标准 | 怎么算完成 |
| **建议** | 错误处理要求 | 容易出错的地方 |
| **建议** | 性能要求 | 超时、并发限制 |

### 4.2 让 AI 代码质量更高的技巧

1. **要求类型注解**：在 Prompt 中明确说"要有完整的类型注解"
2. **要求错误处理**：说"所有可能出错的地方都要有 try/except"
3. **给示例代码**：关键逻辑给一个代码片段作为参考风格
4. **指定设计模式**：如"用策略模式"、"用工厂模式创建 Agent"
5. **要求文档字符串**："每个公共方法都要有 docstring"

### 4.3 常见陷阱

| 陷阱 | 现象 | 解决方案 |
|------|------|----------|
| **AI 忘记导入依赖** | 代码缺少 import | 在 Prompt 中列出需要的 import |
| **AI 用错模型版本** | Pydantic v1 语法 | 明确说"用 Pydantic v2" |
| **AI 生成伪代码** | 省略具体实现 | 说"要写完整实现，不要省略" |
| **AI 忽略错误处理** | 没有 try/except | 明确列出错误场景 |
| **AI 硬编码配置** | API Key 写死在代码里 | 说"从环境变量读取" |
| **AI 用 print** | 调试信息用 print | 说"用 logging 模块" |

---

## 5. 完整 Sprint 的 Prompt 执行顺序

### Sprint 1 执行顺序（有依赖关系）

```
批次 1（无依赖，可并行给 AI）：
├── Prompt: 数据模型 schemas.py
├── Prompt: 项目初始化 (package.json, requirements.txt, 目录结构)
└── Prompt: LLM 客户端 llm_client.py (封装 Kimi/DeepSeek API)

批次 2（依赖批次 1）：
├── Prompt: 工具基类 base.py + MCP 注册中心 tool_registry.py
├── Prompt: 内置工具 (WebSearch, Calculator, CodeExecutor)
└── Prompt: Agent 基类 base.py

批次 3（依赖批次 2）：
├── Prompt: ReAct 引擎 react_loop.py
└── Prompt: 前端骨架 (App.tsx, 路由, 布局)

批次 4（依赖批次 3）：
├── Prompt: FastAPI 主入口 main.py
└── Prompt: 任务 API tasks.py
```

### 实际操作建议

1. **一次只给 AI 一个任务**，等完成后再给下一个
2. **每个任务完成后你审查**，确认 OK 后再继续
3. **遇到 AI 理解偏差**，立即纠正，不要让错误累积
4. **保留每个版本的代码**，方便回滚

---

## 6. 在 OpenCode CLI 中的具体操作

### 6.1 初始化项目

```bash
# 1. 创建项目目录
mkdir -p agent-forge && cd agent-forge

# 2. 初始化后端
mkdir -p backend/agent_forge/{core,agents,tools,mcp,models,api}
touch backend/requirements.txt

# 3. 初始化前端
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install zustand @xyflow/react lucide-react
# 安装 shadcn/ui
npx shadcn@latest init
```

### 6.2 使用 OpenCode CLI 开发

```bash
# 进入项目目录
cd agent-forge

# 启动 OpenCode (假设你已经配置好)
opencode

# 在 OpenCode 交互中，输入 Prompt
# 示例：
> 帮我在 backend/agent_forge/models/schemas.py 中定义以下 Pydantic 模型：
> [粘贴上面 Prompt 1 的内容]

# AI 生成代码后，审查：
> 检查一下类型注解是否完整，Step 模型的 action 字段应该是 Optional[ToolCall]

# 确认 OK 后，让 AI 继续下一个任务
> 现在创建 backend/agent_forge/agents/base.py，实现 Agent 基类...
```

### 6.3 最佳实践

1. **先让 AI 写测试**："先为这个模块写一个 pytest 测试文件"
2. **用测试验证实现**："运行测试看看是否通过"
3. **逐步集成**："现在把这个模块集成到主流程中"
4. **遇到问题让 AI 修复**："运行时报错 xxx，修复一下"

---

## 7. 快速参考：Prompt 模板库

### 模板 A：新建模块

```
新建文件 `{file_path}`，实现以下功能：

【功能描述】

需要实现 {class/function}，接口如下：
```python
{接口定义}
```

依赖的已有代码：
- {依赖文件 1}
- {依赖文件 2}

要求：
- 完整的类型注解
- 所有方法有 docstring
- 错误处理完善
- 用 logging 代替 print
```

### 模板 B：修改现有代码

```
修改文件 `{file_path}`，做以下调整：

当前代码的问题/需要添加的功能：
【具体描述】

修改要求：
- 【要求 1】
- 【要求 2】

注意不要破坏已有功能，保持接口兼容性。
```

### 模板 C：调试修复

```
文件 `{file_path}` 运行时报错：
```
{错误堆栈}
```

复现步骤：
1. 【步骤 1】
2. 【步骤 2】

修复这个错误，并添加相应的错误处理。
```

---

> **总结**：给 AI 写 Prompt 的核心是——**把你想的尽量说清楚，不要假设 AI 知道上下文**。文件路径、接口定义、依赖关系、验收标准，这四样写清楚了，AI 代码质量就会很高。
