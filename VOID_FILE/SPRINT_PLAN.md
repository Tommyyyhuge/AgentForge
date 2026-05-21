# AgentForge 6 周冲刺计划
> **覆盖全部 8 个核心方向**：ReAct、Plan-and-Solve、Reflection、Multi-Agent、MCP、A2A、RAG、Memory

---

## 总体时间线

```
Week 1: Sprint 1 — 基础设施 + 核心引擎 (ReAct)
Week 2: Sprint 2 — 多 Agent 调度 + 前端可视化
Week 3: Sprint 3 — MCP + A2A + Reflection + 记忆系统
Week 4: Sprint 4 — RAG + 协作流程图 + UI 打磨
Week 5: Sprint 5 — 整合测试 + Demo 场景调优
Week 6: Sprint 6 — 文档 + Docker + 部署上线
```

---

## Sprint 1: Week 1 — 基础设施 + 核心引擎
**目标**：后端核心框架可运行，ReAct 引擎能命令行测试通过

### 依赖关系图

```
批次 1 (并行):
├── T1.1 项目骨架初始化
├── T1.2 数据模型 (schemas.py)
└── T1.3 LLM 客户端 (llm_client.py)

批次 2 (依赖批次 1):
├── T1.4 工具基类 + MCP 注册 (tool_registry.py + base.py)
├── T1.5 内置工具 (web_search, calculator, code_executor)
└── T1.6 Agent 基类 (agents/base.py)

批次 3 (依赖批次 2):
├── T1.7 ReAct 引擎 (react_loop.py)
└── T1.8 短期记忆 (short_term_memory.py)

批次 4 (依赖批次 3):
├── T1.9 FastAPI 入口 + API 路由
└── T1.10 前端项目骨架
```

### 任务详情

#### T1.1 项目骨架初始化
- **给 AI 的 Prompt 要点**:
  ```
  创建 AgentForge 项目的目录结构和配置文件：
  
  backend/:
  - requirements.txt (fastapi, uvicorn, pydantic, openai, duckduckgo-search, requests, beautifulsoup4, faiss-cpu, numpy, aiosqlite)
  - agent_forge/__init__.py
  - agent_forge/core/ (ReAct, Planner, Orchestrator, Memory)
  - agent_forge/agents/ (各 Agent 角色)
  - agent_forge/tools/ (工具实现)
  - agent_forge/mcp/ (MCP 工具注册)
  - agent_forge/models/ (数据模型)
  - agent_forge/api/ (FastAPI 路由)
  - run.py (启动脚本)
  
  frontend/: 
  - Vite + React + TypeScript + Tailwind
  - src/components/, src/pages/, src/api/, src/stores/
  
  每个目录下创建 __init__.py
  ```
- **验收标准**: 目录结构完整，backend 能 `python -c "import agent_forge"`
- **预估耗时**: 1h

#### T1.2 数据模型 (schemas.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 1
- **验收标准**: 所有模型能用，类型注解完整
- **预估耗时**: 2h

#### T1.3 LLM 客户端 (llm_client.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 backend/agent_forge/core/llm_client.py：
  
  LLMClient 类，封装 OpenAI 兼容接口：
  - 支持 Kimi K2.6 (api.moonshot.cn) 和 DeepSeek (api.deepseek.com)
  - 从环境变量读取 API Key: KIMI_API_KEY, DEEPSEEK_API_KEY
  - 方法:
    * chat(messages, model, stream, temperature) -> response
    * embed(texts) -> embeddings (用于 RAG)
  - 支持流式输出 (yield chunk)
  - 自动重试（最多3次，指数退避）
  - 超时设置 60s
  - 记录每次调用的 latency 和 token 用量
  ```
- **验收标准**: 能成功调用 Kimi 和 DeepSeek，流式输出正常
- **预估耗时**: 2h

#### T1.4 工具基类 + MCP 注册 (tools/base.py + mcp/tool_registry.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建两个文件：
  
  1. backend/agent_forge/tools/base.py:
     - Tool 抽象基类
     - 属性: name, description (abstract)
     - 方法: get_schema() -> ToolSchema, execute(**kwargs) -> str, validate_arguments(args)
  
  2. backend/agent_forge/mcp/tool_registry.py:
     - ToolRegistry 单例
     - register() 装饰器
     - discover() -> List[ToolSchema]
     - invoke(tool_name, arguments) -> ToolResult
     - 参数校验：用 ToolSchema 校验参数是否合法
  
  ToolSchema 在 schemas.py 中定义，包含 name, description, parameters (JSON Schema), required, returns
  ```
- **验收标准**: 能用装饰器注册工具，discover 和 invoke 正常工作
- **预估耗时**: 2h

#### T1.5 内置工具 (tools/web_search.py, calculator.py, code_executor.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 5
- **特别注意 CodeExecutorTool**:
  ```
  安全性要求：
  - 用 subprocess 运行，超时 30s
  - 禁止的模块：os, sys, subprocess, pathlib, shutil
  - 用 ast 检查 import 语句
  - 捕获所有异常，不泄露系统信息
  ```
- **验收标准**: 三个工具都能独立运行，CodeExecutor 有安全限制
- **预估耗时**: 3h

#### T1.6 Agent 基类 (agents/base.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 2
- **验收标准**: execute 方法编排完整流程，能正确调用 ReActLoop
- **预估耗时**: 3h

#### T1.7 ReAct 引擎 (core/react_loop.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 3
- **验收标准**:
  - 命令行测试：输入简单任务，能看到 Thought → Action → Observation → Final Answer
  - 流式事件正确 yield
  - 达到 max_steps 时优雅结束
- **预估耗时**: 4h

#### T1.8 短期记忆 (core/short_term_memory.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 backend/agent_forge/core/short_term_memory.py：
  
  ShortTermMemory 类：
  - 属性: turns (列表，最多保留 max_turns 条)
  - 方法:
    * add(result: ExecutionResult): 添加一轮执行记录
    * get_context() -> str: 获取当前上下文的文本表示
    * search(query: str, top_k: int) -> List[Turn]: 关键词搜索相关记录
    * clear(): 清空记忆
  
  Turn 模型:
  - role: str, content: str, steps: List[Step], timestamp: datetime
  ```
- **验收标准**: 能存储和检索对话历史
- **预估耗时**: 1.5h

#### T1.9 FastAPI 入口 (api/main.py + api/tasks.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 FastAPI 应用：
  
  1. backend/agent_forge/api/main.py:
     - FastAPI 实例，CORS 配置
     - 包含 routers
     - 健康检查端点 GET /health
  
  2. backend/agent_forge/api/tasks.py:
     - POST /api/tasks: 创建任务 (接收 {task: str})
     - GET /api/tasks/{id}: 获取任务状态
     - GET /api/tasks/{id}/stream: SSE 流式执行 (核心！)
     - GET /api/tasks/{id}/result: 获取最终结果
     
  SSE 端点要点：
  - 用 StreamingResponse
  - 每次 yield 一个 SSEEvent 的 JSON
  - 连接断开时优雅处理
  ```
- **验收标准**: API 能用 curl 测试，SSE 端点能收到事件流
- **预估耗时**: 3h

#### T1.10 前端骨架
- **给 AI 的 Prompt 要点**:
  ```
  创建前端骨架：
  
  1. 主布局 (src/App.tsx):
     - 左侧边栏 (25%): 历史任务列表
     - 主内容区 (75%): 动态内容
     - 顶部导航栏
  
  2. 状态管理 (src/stores/taskStore.ts):
     - 用 Zustand
     - 状态: currentTask, agents, events, isRunning
     - 方法: createTask, connectSSE, disconnectSSE
  
  3. API 层 (src/api/taskApi.ts):
     - createTask(task: string) -> taskId
     - connectSSE(taskId, onEvent) -> EventSource
  
  4. 任务输入组件 (src/components/TaskInput.tsx):
     - 文本输入框 + 执行按钮
     - 预设场景下拉选择
  
  用 Tailwind 做基础样式，shadcn/ui 的 Button, Input, Card 组件
  ```
- **验收标准**: 页面能显示，能输入任务并发送到后端
- **预估耗时**: 4h

### Sprint 1 验收清单
- [ ] 后端能 `python run.py` 启动，FastAPI 运行正常
- [ ] ReAct 引擎命令行测试通过（输入简单任务，能看到完整推理链）
- [ ] MCP 工具注册和调用正常
- [ ] 前端页面能访问，能创建任务
- [ ] SSE 连接能收到事件

---

## Sprint 2: Week 2 — 多 Agent 调度 + 前端可视化
**目标**：多 Agent 协作跑通，前端能实时展示 Agent 执行过程

### 任务详情

#### T2.1 Planner Agent (agents/planner_agent.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 PlannerAgent，继承 BaseAgent：
  
  角色：任务规划师
  系统提示词：
  "你是一位专业的任务规划师。你的职责是将复杂任务拆解为可执行的子任务。"
  
  核心功能：
  - 接收用户任务，输出 Plan 对象
  - 输出格式：JSON，包含 complexity_score, subtasks[]
  - 每个子任务包含: id, description, assigned_agent, dependencies[], estimated_complexity
  
  可用的 agent 角色：
  - researcher: 信息搜索和整理
  - coder: 编写和执行代码
  - writer: 撰写报告和文案
  - reviewer: 审查质量
  
  规划原则：
  1. 每个子任务原子性
  2. 明确依赖关系
  3. 预估复杂度 (0-1)
  ```
- **验收标准**: 输入任务后，能输出包含子任务的 JSON Plan
- **预估耗时**: 3h

#### T2.2 Orchestrator 调度器 (core/orchestrator.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 4
- **验收标准**:
  - 能按依赖顺序调度
  - 无依赖的子任务并行执行
  - yield 完整的事件流
- **预估耗时**: 5h

#### T2.3 Researcher + Coder + Writer Agent
- **给 AI 的 Prompt 要点**:
  ```
  创建三个 Agent，都继承 BaseAgent：
  
  1. ResearcherAgent (agents/researcher_agent.py):
     - 角色：研究员
     - 工具：WebSearchTool, BrowserTool
     - 系统提示词：强调搜索技巧、信息筛选、来源引用
  
  2. CoderAgent (agents/coder_agent.py):
     - 角色：程序员
     - 工具：CodeExecutorTool, CalculatorTool
     - 系统提示词：强调代码质量、错误处理、测试
  
  3. WriterAgent (agents/writer_agent.py):
     - 角色：撰写员
     - 工具：无（纯写作）
     - 系统提示词：强调结构化写作、逻辑清晰
  
  每个 Agent：
  - 有专门的系统提示词
  - 有自己的工具集
  - execute 方法继承基类（复用 ReAct + Reflection）
  ```
- **验收标准**: 三个 Agent 能独立执行各自类型的任务
- **预估耗时**: 4h

#### T2.4 Reviewer Agent (agents/reviewer_agent.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 ReviewerAgent：
  
  - 角色：质量审查员
  - 工具：无
  - 核心功能：
    * 审查其他 Agent 的输出质量
    * 检查事实准确性
    * 评估完整性和逻辑性
    * 返回审查报告：通过/需修改 + 具体建议
  
  系统提示词：
  "你是一位严格的质量审查员。你的职责是审查其他 Agent 的工作成果，
   确保准确性、完整性和逻辑性。发现问题时给出具体的修改建议。"
  ```
- **验收标准**: 能审查并返回结构化报告
- **预估耗时**: 1.5h

#### T2.5 SSE 流式推送完善 (api/stream.py)
- **给 AI 的 Prompt 要点**:
  ```
  完善 SSE 流式输出：
  
  需要推送的事件类型（按时间顺序）：
  1. plan_created: Plan 已创建
  2. agent_started: Agent 开始执行
  3. thought: Agent 思考
  4. action: Agent 采取行动
  5. observation: 获取观察结果
  6. agent_completed: Agent 完成
  7. subtask_completed: 子任务完成
  8. final_result: 最终结果
  
  每个事件包含：type, timestamp, agent(可选), content/data
  
  实现要点：
  - 用 asyncio.Queue 作为事件队列
  - Orchestrator 产生事件 → 入队 → SSE 消费
  - 连接断开时清理资源
  ```
- **验收标准**: 前端能收到完整的事件流，顺序正确
- **预估耗时**: 3h

#### T2.6 AgentMonitor 组件 (frontend/src/components/AgentMonitor.tsx)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md Prompt 6
- **验收标准**:
  - 实时显示 Agent 状态
  - Thought/Action/Observation 区分清晰
  - 打字机效果流畅
- **预估耗时**: 5h

#### T2.7 任务计划展示组件 (frontend/src/components/TaskPlan.tsx)
- **给 AI 的 Prompt 要点**:
  ```
  创建 TaskPlan 组件：
  
  功能：展示 Planner 生成的子任务列表
  
  1. 子任务卡片：
     - 序号、描述、分配的 Agent、复杂度
     - 状态标识：pending/running/completed/failed
     - 依赖关系可视化（小箭头连接）
  
  2. 整体进度条：
     - 显示完成比例
  
  3. 交互：
     - 点击子任务展开详情
     - 实时更新状态
  
  数据从 taskStore 中获取 plan 数据
  ```
- **验收标准**: 能正确展示子任务和依赖关系
- **预估耗时**: 2h

### Sprint 2 验收清单
- [ ] 输入复杂任务，Planner 能拆解为多个子任务
- [ ] Orchestrator 按依赖顺序调度 Agent 执行
- [ ] 前端 AgentMonitor 能实时显示 ReAct 过程
- [ ] 完整跑通一个多步骤任务

---

## Sprint 3: Week 3 — MCP + A2A + Reflection + 记忆系统
**目标**：完整实现 MCP 工具体系、A2A 通信、反思引擎、三层记忆

### 任务详情

#### T3.1 MCP 工具完善 (mcp/tool_registry.py + tools/*)
- **给 AI 的 Prompt 要点**:
  ```
  完善 MCP 体系：
  
  1. 给所有工具添加完整的 JSON Schema:
     - WebSearchTool: {query: string, max_results?: number}
     - CalculatorTool: {expression: string}
     - CodeExecutorTool: {code: string, timeout?: number}
     - BrowserTool: {url: string}
  
  2. ToolRegistry 添加：
     - get_tool_schema(tool_name) -> 单个工具的 schema
     - validate_arguments(tool_name, args) -> bool 验证参数
  
  3. 创建 MCP 风格的 tools/list 端点:
     GET /api/tools -> 返回所有工具的 schema 列表
  
  4. Agent 的 ReAct prompt 中，工具描述用 JSON Schema 格式
  ```
- **验收标准**: GET /api/tools 返回正确的工具描述
- **预估耗时**: 3h

#### T3.2 A2A 消息总线 (core/a2a_bus.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 A2A 风格的消息总线：
  
  文件: backend/agent_forge/core/a2a_bus.py
  
  A2ABus 类：
  
  1. 属性:
     - _agents: Dict[str, BaseAgent] (已注册 Agent)
     - _capabilities: Dict[str, List[str]] (Agent → 能力列表)
     - _queues: Dict[str, asyncio.Queue] (Agent → 消息队列)
  
  2. 核心方法:
     - register(agent_id, capabilities, agent_ref): 注册 Agent
     - discover(capability=None): 发现 Agent
     - send(message): 路由消息到目标 Agent
     - handoff(from, to, task, context): 任务移交
     - get_queue(agent_id): 获取 Agent 消息队列
  
  3. 消息类型支持:
     - task: 任务分配
     - result: 结果返回
     - query: 查询请求
     - feedback: 反馈
     - handoff: 任务移交
  
  4. 在 Orchestrator 中集成:
     - Agent 执行前先注册到 A2A Bus
     - Agent 间通信通过 A2A Bus 路由
  
  5. 前端展示：
     - 添加 Agent 间消息的事件类型
     - SSE 推送 agent_message 事件
  ```
- **验收标准**:
  - Agent 能注册和发现
  - 消息能正确路由
  - handoff 能移交任务
- **预估耗时**: 4h

#### T3.3 Reflection 引擎 (core/reflection_engine.py)
- **给 AI 的 Prompt 要点**: 见 AGENT_PROMPT_GUIDE.md（3.3 Reflection 部分）
- **验收标准**:
  - 能对执行结果生成反思报告
  - 评分维度完整 (0-10)
  - 建议具体可执行
- **预估耗时**: 3h

#### T3.4 长期记忆 + 经验记忆 (core/long_term_memory.py + experience_memory.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建三层记忆系统：
  
  文件 1: backend/agent_forge/core/long_term_memory.py
  LongTermMemory 类：
  - 使用 SQLite 存储 (aiosqlite)
  - 表: memories (id, task, answer, steps_summary, reflection_score, embedding_json, created_at)
  - 方法:
    * store(task, result): 存储执行记录
    * search(query, top_k): 用关键词 + 分数排序检索
  
  文件 2: backend/agent_forge/core/experience_memory.py
  ExperienceMemory 类：
  - 表: experiences (id, lessons_learned, improvement_suggestions, avg_score, created_at)
  - 方法:
    * store(reflection): 从反思报告提取经验
    * search(query, top_k): 关键词搜索相关经验
  
  文件 3: backend/agent_forge/core/memory_manager.py
  MemoryManager 类：
  - 组合三层记忆: short_term, long_term, experience
  - 统一接口:
    * store(task, result): 存入所有三层
    * search(query, top_k): 从三层分别检索，合并排序
  
  创建数据库初始化脚本: backend/agent_forge/database/init_db.py
  ```
- **验收标准**:
  - 数据能正确存入 SQLite
  - 检索返回相关结果
  - 三层记忆协同工作
- **预估耗时**: 4h

#### T3.5 反思报告组件 (frontend/src/components/ReflectionReport.tsx)
- **给 AI 的 Prompt 要点**:
  ```
  创建 ReflectionReport 组件：
  
  展示内容：
  1. 综合评分（大数字显示，颜色根据分数变化）
  2. 雷达图：各维度评分（效率、决策、错误处理、输出质量）
  3. 做得好的地方 (strengths) - 绿色列表
  4. 不足之处 (weaknesses) - 橙色列表
  5. 改进建议 (improvement_suggestions) - 可点击标记为"已采纳"
  6. 经验总结 (lessons_learned) - 引用样式展示
  
  用 recharts 画雷达图
  数据从 taskStore.reflection 获取
  ```
- **预估耗时**: 2.5h

#### T3.6 记忆检索组件 (frontend/src/components/MemorySearch.tsx)
- **给 AI 的 Prompt 要点**:
  ```
  创建 MemorySearch 组件：
  
  功能：
  1. 搜索输入框
  2. 搜索按钮
  3. 结果列表：
     - 相关历史任务
     - 显示相似度分数
     - 可点击查看详情
  4. 切换三层记忆：短期 / 长期 / 经验
  
  API: GET /api/memory/search?query=xxx&top_k=5
  ```
- **预估耗时**: 2h

### Sprint 3 验收清单
- [ ] MCP 工具发现和调用可演示
- [ ] A2A Agent 间通信可演示
- [ ] Reflection 报告完整
- [ ] 记忆系统能存储和检索
- [ ] 前端新增 Reflection 和 Memory 页面

---

## Sprint 4: Week 4 — RAG + 协作流程图 + UI 打磨
**目标**：RAG 检索增强跑通，协作流程图完整，UI 美观

### 任务详情

#### T4.1 RAG 系统 (core/rag_system.py)
- **给 AI 的 Prompt 要点**:
  ```
  创建 RAG 系统：
  
  文件: backend/agent_forge/core/rag_system.py
  
  RAGSystem 类：
  
  1. 文档处理:
     - add_documents(docs: List[Document]): 添加文档
     - 自动切分长文档 (chunk_size=500, overlap=50)
  
  2. 向量化:
     - 用 LLMClient.embed() 生成向量
     - FAISS 索引 (faiss.IndexFlatIP 内积)
  
  3. 检索:
     - search(query, top_k=5): 向量化查询 → FAISS 检索
     - 返回 RetrievalResult[] (document, similarity_score)
  
  4. Agent 集成:
     - BaseAgent.execute 中，任务执行前先 RAG 检索
     - 检索结果注入上下文
  
  Document 模型:
  - id, content, metadata, source
  
  RetrievalResult 模型:
  - document: Document, similarity_score: float
  
  添加 API:
  - POST /api/rag/documents: 添加文档
  - GET /api/rag/search?query=xxx: 检索
  ```
- **验收标准**: 添加文档后能检索到相关结果
- **预估耗时**: 4h

#### T4.2 协作流程图 (frontend/src/components/CollaborationGraph.tsx)
- **给 AI 的 Prompt 要点**:
  ```
  创建协作流程图组件（用 @xyflow/react）：
  
  功能：
  1. 节点：每个 Agent 一个节点
     - 不同颜色区分角色
     - 显示 Agent 名称和状态
     - 当前激活的 Agent 有脉冲动画
  
  2. 边：Agent 间的消息传递
     - 有向边，带箭头
     - 消息流动画（虚线流动）
     - 边上显示消息类型
  
  3. 数据驱动：
     - 从 taskStore 的 agents 和 messages 生成 nodes 和 edges
     - 实时更新（SSE 事件驱动）
  
  4. 交互：
     - 点击节点查看 Agent 详情
     - 拖拽调整布局
     - 自动适配视图
  
  节点样式：
  - Planner: 紫色
  - Researcher: 蓝色
  - Coder: 绿色
  - Writer: 橙色
  - Reviewer: 红色
  ```
- **验收标准**: 流程图能动态展示 Agent 协作
- **预估耗时**: 5h

#### T4.3 工具调用日志 (frontend/src/components/ToolLog.tsx)
- **给 AI 的 Prompt 要点**:
  ```
  创建 ToolLog 组件：
  
  时间线形式展示工具调用：
  1. 每条记录：
     - 时间戳
     - 调用 Agent
     - 工具名（带图标）
     - 输入参数（可展开）
     - 返回结果（可展开，太长时截断）
     - 耗时
  
  2. 筛选：
     - 按 Agent 筛选
     - 按工具类型筛选
  
  3. 搜索：
     - 关键词搜索
  
  数据从 taskStore 的 toolCalls 获取
  ```
- **预估耗时**: 2h

#### T4.4 UI 美化 + 响应式
- **给 AI 的 Prompt 要点**:
  ```
  美化整体 UI：
  
  1. 主题色：深色模式为主（Agent 监控系统感）
     - 背景: slate-950
     - 卡片: slate-900
     - 强调色: indigo-500
  
  2. 动画：
     - 页面切换过渡
     - 卡片悬停效果
     - 加载动画
  
  3. 字体：
     - 代码用 JetBrains Mono
     - 正文用 Inter
  
  4. 响应式：
     - 小屏幕时侧边栏收起
     - 主内容区自适应
  
  5. 空状态：
     - 各面板在无数据时的友好提示
  
  用 Tailwind 的 dark mode
  ```
- **预估耗时**: 4h

### Sprint 4 验收清单
- [ ] RAG 能添加文档并检索
- [ ] 协作流程图动态展示
- [ ] 工具日志完整
- [ ] UI 美观专业

---

## Sprint 5: Week 5 — 整合测试 + Demo 场景调优
**目标**：四个 Demo 场景稳定跑通，系统健壮

### 任务详情

#### T5.1 Demo 场景 1：调研分析
- **测试输入**: "调研 2025 年 AI Agent 领域的主流框架，对比 AutoGen、CrewAI、LangGraph 的优缺点"
- **调优要点**:
  - 调优 Researcher 的系统提示词（搜索策略）
  - 调优 Writer 的整合逻辑
  - 确保 Reviewer 能发现事实错误
- **预估耗时**: 3h

#### T5.2 Demo 场景 2：编程任务
- **测试输入**: "写一个 Python 函数，输入一个 URL，返回网页中所有图片链接，要求处理相对路径"
- **调优要点**:
  - Coder 的代码生成质量
  - CodeExecutor 的安全性
  - 错误处理和重试
- **预估耗时**: 3h

#### T5.3 Demo 场景 3：内容创作
- **测试输入**: "帮我写一篇关于 MCP 协议的技术博客，要求通俗易懂，适合初学者"
- **调优要点**:
  - Researcher 的资料收集
  - Writer 的写作风格
  - Reviewer 的质量把关
- **预估耗时**: 2h

#### T5.4 Demo 场景 4：数据分析
- **测试输入**: "分析这个 CSV 文件的销售数据，找出趋势并可视化" (提供一个测试 CSV)
- **调优要点**:
  - Coder 的数据处理
  - 图表生成
  - 报告撰写
- **预估耗时**: 3h

#### T5.5 错误处理强化
- **给 AI 的 Prompt 要点**:
  ```
  强化错误处理：
  
  1. LLM 调用：
     - 超时重试（指数退避：1s, 2s, 4s）
     - 格式错误时重新生成
     - 连续失败时降级到备用模型
  
  2. 工具执行：
     - 超时处理
     - 异常捕获
     - 返回友好的错误信息
  
  3. Agent 执行：
     - 单步失败不影响整体
     - 失败子任务的重试和重新规划
     - 最终失败的优雅降级
  
  4. SSE 连接：
     - 自动重连
     - 连接断开时清理
  ```
- **预估耗时**: 4h

#### T5.6 性能优化
- **给 AI 的 Prompt 要点**:
  ```
  性能优化：
  
  1. 并行执行优化：
     - 无依赖子任务真正并行
     - asyncio.gather 优化
  
  2. LLM 调用优化：
     - 合理的超时设置
     - 连接池复用
  
  3. 前端优化：
     - 虚拟列表（历史任务多时）
     - 事件节流（SSE 事件密集时）
  ```
- **预估耗时**: 3h

### Sprint 5 验收清单
- [ ] 四个 Demo 场景都能稳定跑通
- [ ] LLM 调用失败有重试和降级
- [ ] 工具执行有超时和安全限制
- [ ] SSE 连接稳定

---

## Sprint 6: Week 6 — 文档 + Docker + 部署上线
**目标**：项目文档完整，可在线访问

### 任务详情

#### T6.1 README.md
- **给 AI 的 Prompt 要点**:
  ```
  编写专业的 README.md：
  
  内容结构：
  1. 项目标题 + 一句话描述
  2. 项目截图 (先占位)
  3. 核心特性列表 (8 个方向)
  4. 技术栈
  5. 架构图 (用 mermaid)
  6. 快速开始 (安装、配置、运行)
  7. Demo 场景说明
  8. 项目结构
  9. 贡献指南
  10. License
  
  要专业、简洁、有吸引力
  ```
- **预估耗时**: 2h

#### T6.2 ARCHITECTURE.md
- **给 AI 的 Prompt 要点**:
  ```
  编写架构文档：
  
  内容：
  1. 系统架构图 (mermaid)
  2. 核心模块说明
  3. 数据流图
  4. Agent 协作流程
  5. 技术决策记录 (为什么选 FastAPI? 为什么自研调度器?)
  6. 扩展指南 (如何添加新 Agent 角色? 如何添加新工具?)
  ```
- **预估耗时**: 2h

#### T6.3 Dockerfile + docker-compose.yml
- **给 AI 的 Prompt 要点**:
  ```
  创建 Docker 配置：
  
  1. backend/Dockerfile:
     - Python 3.11 slim
     - 安装依赖
     - 暴露 8000 端口
     - 启动命令
  
  2. frontend/Dockerfile:
     - Node 20
     - 构建生产版本
     - Nginx 服务
  
  3. docker-compose.yml:
     - backend 服务
     - frontend 服务
     - 共享网络
     - 环境变量配置
  
  4. .dockerignore
  ```
- **预估耗时**: 2h

#### T6.4 部署
- **前端**: Vercel (`npm run build` → 部署到 Vercel)
- **后端**: Render 或 Railway
- **预估耗时**: 2h

#### T6.5 最终测试
- 在部署环境中完整测试四个 Demo 场景
- 预估耗时**: 3h

### Sprint 6 验收清单
- [ ] README 专业完整
- [ ] Docker 一键启动
- [ ] Web Demo 可在线访问
- [ ] 四个场景在部署环境稳定运行

---

## 总时间预估

| Sprint | 任务数 | 预估总耗时 | 你的可用时间 (5-8h/天) |
|--------|--------|-----------|----------------------|
| Sprint 1 | 10 | ~25h | 3-4 天 |
| Sprint 2 | 7 | ~23h | 3-4 天 |
| Sprint 3 | 6 | ~19h | 3 天 |
| Sprint 4 | 4 | ~15h | 2-3 天 |
| Sprint 5 | 6 | ~19h | 3 天 |
| Sprint 6 | 5 | ~11h | 2 天 |
| **总计** | **38** | **~112h** | **16-19 天 (约 3 周)** |

> 按你每天 5-8 小时算，实际需要 **3-4 周**。预留 buffer 给 AI 出错重试、调试、优化，**6 周计划是合理的**。

---

## 每周节奏建议

```
周一:
  - 上午：回顾上周成果，更新任务状态
  - 下午：给 AI 下发本周第一批任务

周二-周四:
  - 每天给 AI 2-3 个任务
  - 审查 AI 输出，测试，反馈修复

周五:
  - 整合本周代码
  - 跑通本周的功能测试
  - 更新进度，规划下周

周末:
  - 选做：UI 打磨、文档、额外优化
  - 或休息，保持可持续节奏
```

---

## 风险应对

| 风险 | 应对 |
|------|------|
| 某周任务没完成 | 优先保证核心功能（ReAct + Multi-Agent），其他可延期 |
| LLM API 不稳定 | 同时配置 Kimi 和 DeepSeek 作为备用 |
| AI 生成代码质量差 | 细化 Prompt，提供更详细的接口定义和示例 |
| 前端比预期复杂 | 优先保证功能，UI 可以后期打磨 |
| Docker 部署问题 | 本地可运行也是有效 Demo，部署可延后 |

---

> **下一步**：确认这个计划后，我会为你生成 Sprint 1 的完整 Prompt 序列（可以直接复制粘贴到 OpenCode 中执行）
