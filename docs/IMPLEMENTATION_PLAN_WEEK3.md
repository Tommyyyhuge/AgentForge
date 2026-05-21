# Week 3 详细实施计划

> **版本**: 1.0
> **日期**: 2026-05-21
> **基于**: docs/superpowers/specs/2026-05-21-week3-design.md
> **目标**: 文件级实施清单，包含代码结构、测试要点、依赖关系

---

## 目录

1. [执行策略](#1-执行策略)
2. [Day 1: 核心 MCP 工具](#2-day-1-核心-mcp-工具)
3. [Day 2: 补充工具 + 测试](#3-day-2-补充工具--测试)
4. [Day 3: JWT 认证 + 新 Agent 角色](#4-day-3-jwt-认证--新-agent-角色)
5. [Day 4: Memory 系统](#5-day-4-memory-系统)
6. [Day 5: RAG 系统](#6-day-5-rag-系统)
7. [Day 6: Reflection 引擎](#7-day-6-reflection-引擎)
8. [Day 7: 前端完整功能](#8-day-7-前端完整功能)
9. [Day 8: 联调 + 性能优化](#9-day-8-联调--性能优化)
10. [并行执行建议](#10-并行执行建议)
11. [风险缓解](#11-风险缓解)

---

## 1. 执行策略

### 1.1 核心原则

- **质量优先**：6个高质量工具 > 8个半成品
- **Memory先于RAG**：避免重复实现向量存储
- **JWT提前**：Day 3完成认证，后续API都有保护
- **测试驱动**：每个模块先写测试，再写实现

### 1.2 模块依赖图

```
Week 3 实施依赖图:

Day 1 ───────────────────────────────────────┐
├─ tools/code_execute.py                      │
│   └─ 依赖: tools/base.py                     │
├─ tools/file_io.py                           │
│   └─ 依赖: tools/base.py                     │
├─ tools/summarize.py                         │
│   └─ 依赖: tools/base.py, llm_client.py     │
└─ tools/agent_message.py                     │
    └─ 依赖: tools/base.py, a2a_bus.py        │
                                              │
Day 2 ───────────────────────────────────────┤
├─ tools/memory_search.py (Mock)              │
│   └─ 依赖: tools/base.py                     │
├─ tools/web_browser.py                       │
│   └─ 依赖: tools/base.py, httpx             │
└─ tools/web_search.py (真实化)               │
    └─ 依赖: tools/base.py, duckduckgo-search │
                                              │
Day 3 ───────────────────────────────────────┤
├─ api/routes/auth.py                         │
│   └─ 依赖: models/schemas.py, database      │
├─ database/models.py (更新)                  │
│   └─ 依赖: database/connection.py           │
├─ agents/coder_agent.py                      │
│   └─ 依赖: agents/base.py, tools            │
├─ agents/writer_agent.py                     │
│   └─ 依赖: agents/base.py, tools            │
└─ agents/reviewer_agent.py                   │
    └─ 依赖: agents/base.py, tools            │
                                              │
Day 4 ───────────────────────────────────────┤
├─ core/memory_manager.py                     │
│   └─ 依赖: llm_client.py, chromadb          │
└─ database/models.py (更新: MemoryORM)       │
    └─ 依赖: database/connection.py           │
                                              │
Day 5 ───────────────────────────────────────┤
├─ core/rag_system.py                         │
│   └─ 依赖: memory_manager.py                │
└─ tools/memory_search.py (更新: 接入RAG)     │
    └─ 依赖: rag_system.py                    │
                                              │
Day 6 ───────────────────────────────────────┤
├─ core/reflection_engine.py                  │
│   └─ 依赖: llm_client.py, memory_manager    │
└─ core/orchestrator.py (更新: 集成Reflection)│
    └─ 依赖: reflection_engine.py             │
                                              │
Day 7 ───────────────────────────────────────┤
└─ frontend/                                  │
    ├─ pages/AgentMonitor.tsx                 │
    ├─ pages/MultiAgentChat.tsx               │
    ├─ pages/Settings.tsx                     │
    ├─ stores/authStore.ts                    │
    └─ api/client.ts (更新)                   │
                                              │
Day 8 ───────────────────────────────────────┤
├─ api/middleware/rate_limit.py               │
├─ tests/                                     │
└─ 联调、性能优化                             │
```

---

## 2. Day 1: 核心 MCP 工具

### 2.1 tools/code_execute.py

**目标**: 安全沙箱执行Python代码

**实现步骤**:

1. **定义安全策略**
   - FORBIDDEN_MODULES = {'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests'}
   - FORBIDDEN_FUNCTIONS = {'eval', 'exec', 'compile', '__import__', 'open'}

2. **实现安全检查**
   - `_is_safe_code(code)` - AST解析检查禁止的import和函数调用
   - 处理SyntaxError

3. **实现子进程执行**
   - `_run_in_subprocess(code, timeout)` - subprocess.run隔离执行
   - 工作目录限制：`cwd='./workspace'`
   - 超时控制：默认30秒

4. **实现execute方法**
   - 安全检查 → 子进程执行 → 输出截断（10000字符）
   - 返回stdout + stderr

**代码结构**:
```python
class CodeExecuteTool(BaseTool):
    name = "code_execute"
    description = "安全执行Python代码并返回结果"
    
    FORBIDDEN_MODULES = {...}
    FORBIDDEN_FUNCTIONS = {...}
    MAX_OUTPUT_LENGTH = 10000
    DEFAULT_TIMEOUT = 30
    
    def _build_schema(self) -> ToolSchema: ...
    async def execute(self, code: str, timeout: int = 30) -> str: ...
    def _is_safe_code(self, code: str) -> bool: ...
    async def _run_in_subprocess(self, code: str, timeout: int) -> str: ...
```

**测试要点**:
- test_safe_code_execution: 正常代码执行
- test_forbidden_import: 禁止的import检测
- test_forbidden_function: 禁止的函数调用检测
- test_timeout: 超时处理
- test_output_truncation: 输出截断
- test_syntax_error: 语法错误处理

**时间估算**: 3-4 小时

---

### 2.2 tools/file_io.py

**目标**: 安全的文件读写操作

**实现步骤**:

1. **定义安全限制**
   - ALLOWED_DIR = Path("./workspace").resolve()
   - MAX_FILE_SIZE = 10MB

2. **实现路径检查**
   - `_sanitize_path(path)` - 确保路径在ALLOWED_DIR内
   - 防止路径遍历攻击（../../../etc/passwd）

3. **实现FileReadTool**
   - execute(path, limit=1000) - 读取文件前limit行
   - 文件大小检查

4. **实现FileWriteTool**
   - execute(path, content) - 写入文件
   - 自动创建父目录
   - 内容大小检查

**代码结构**:
```python
class FileReadTool(BaseTool):
    name = "file_read"
    ALLOWED_DIR = Path("./workspace").resolve()
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def _sanitize_path(self, path: str) -> Path: ...
    async def execute(self, path: str, limit: int = 1000) -> str: ...

class FileWriteTool(BaseTool):
    name = "file_write"
    ALLOWED_DIR = Path("./workspace").resolve()
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def _sanitize_path(self, path: str) -> Path: ...
    async def execute(self, path: str, content: str) -> str: ...
```

**测试要点**:
- test_read_file: 正常读取
- test_write_file: 正常写入
- test_path_traversal: 路径遍历攻击防护
- test_file_size_limit: 文件大小限制
- test_outside_allowed_dir: 目录外访问阻止

**时间估算**: 2 小时

---

### 2.3 tools/summarize.py

**目标**: 使用LLM对长文本进行摘要

**实现步骤**:

1. **实现文本长度检查**
   - 短文本（<500字）直接返回，不摘要
   - 长文本调用LLM

2. **实现LLM摘要**
   - 构建摘要提示
   - 调用LLM（使用llm_client.py）
   - 处理LLM响应

3. **优化策略**
   - 支持指定摘要长度和风格
   - 超长文本分段摘要（可选）

**代码结构**:
```python
class SummarizeTool(BaseTool):
    name = "summarize"
    description = "对长文本进行摘要"
    MIN_SUMMARIZE_LENGTH = 500
    
    def __init__(self, llm_router: LLMRouter = None):
        self.llm_router = llm_router
    
    def _build_schema(self) -> ToolSchema: ...
    async def execute(self, text: str, max_length: int = 200) -> str: ...
    def _build_prompt(self, text: str, max_length: int) -> str: ...
```

**测试要点**:
- test_short_text: 短文本直接返回
- test_long_text: 长文本摘要
- test_llm_error: LLM调用失败处理

**时间估算**: 1.5 小时

---

### 2.4 tools/agent_message.py

**目标**: 封装A2A Bus，让Agent通过工具调用发送消息

**实现步骤**:

1. **初始化A2A Bus引用**
   - `__init__(a2a_bus: A2ABus)`

2. **实现消息发送**
   - execute(receiver_role, message)
   - 查找对应角色的Agent
   - 构造A2AMessage
   - 通过A2A Bus发送

3. **处理响应**
   - 可选：等待响应（带超时）
   - 返回发送结果

**代码结构**:
```python
class AgentMessageTool(BaseTool):
    name = "agent_message"
    description = "发送消息给其他Agent"
    
    def __init__(self, a2a_bus: A2ABus):
        self.a2a_bus = a2a_bus
    
    def _build_schema(self) -> ToolSchema: ...
    async def execute(self, receiver_role: str, message: str) -> str: ...
```

**测试要点**:
- test_send_message: 消息发送
- test_invalid_role: 无效角色处理

**时间估算**: 1.5 小时

**Day 1 总计**: 8-10 小时

---

## 3. Day 2: 补充工具 + 测试

### 3.1 tools/memory_search.py (Mock)

**目标**: 记忆检索工具（Day 2 Mock，Day 5接入真实RAG）

**实现步骤**:

1. **Mock实现**
   - 预设记忆片段字典
   - 根据query关键词匹配
   - 返回前N个结果

2. **接口预留**
   - 构造函数接受rag_system参数（可选）
   - 如果rag_system为None，使用Mock

**代码结构**:
```python
class MemorySearchTool(BaseTool):
    name = "memory_search"
    description = "搜索历史记忆和知识库"
    
    def __init__(self, rag_system=None):
        self.rag_system = rag_system
        self._mock_memories = {...}
    
    def _build_schema(self) -> ToolSchema: ...
    async def execute(self, query: str, limit: int = 5) -> str: ...
```

**时间估算**: 1 小时

---

### 3.2 tools/web_browser.py

**目标**: 网页浏览和内容抓取

**实现步骤**:

1. **发送HTTP请求**
   - 使用httpx获取网页
   - 处理超时和错误

2. **解析HTML**
   - 使用beautifulsoup4
   - 提取正文文本（去除script/style/nav等）
   - 限制返回长度

**代码结构**:
```python
class WebBrowserTool(BaseTool):
    name = "web_browser"
    description = "浏览网页并提取内容"
    
    def _build_schema(self) -> ToolSchema: ...
    async def execute(self, url: str) -> str: ...
    def _extract_text(self, html: str) -> str: ...
```

**测试要点**:
- test_browse_webpage: 正常网页抓取
- test_invalid_url: 无效URL处理
- test_timeout: 超时处理

**时间估算**: 1.5 小时

---

### 3.3 tools/web_search.py (真实化)

**目标**: 将Week 2的Mock替换为真实DuckDuckGo搜索

**实现步骤**:

1. **接入duckduckgo-search**
   - 使用DDGS().text()方法
   - 处理搜索结果

2. **格式化输出**
   - 提取标题、摘要、URL
   - 返回格式化的字符串

**代码结构**:
```python
class WebSearchTool(BaseTool):
    name = "web_search"
    
    async def execute(self, query: str, max_results: int = 5) -> str:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
        return self._format_results(results)
```

**时间估算**: 1 小时

---

### 3.4 工具测试

**测试文件**: `tests/unit/test_tools.py`

覆盖6个新工具的测试，每个工具2-3个测试用例。

**时间估算**: 3-4 小时

**Day 2 总计**: 6-7.5 小时

---

## 4. Day 3: JWT 认证 + 新 Agent 角色

### 4.1 api/routes/auth.py

**目标**: JWT认证API（注册/登录/获取当前用户）

**实现步骤**:

1. **Pydantic模型**
   - RegisterRequest: username, password, email
   - LoginRequest: username, password
   - TokenResponse: access_token, token_type, expires_in
   - UserResponse: id, username, email

2. **JWT工具函数**
   - create_access_token(data, expires_delta)
   - decode_token(token)
   - get_current_user(token) - FastAPI依赖

3. **密码哈希**
   - 使用passlib[bcrypt]
   - hash_password(password)
   - verify_password(plain, hashed)

4. **API端点**
   - POST /register
   - POST /login
   - GET /me

5. **数据库模型**
   - UserORM: id, username, email, hashed_password, is_active, created_at

**代码结构**:
```python
# JWT配置
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# 工具函数
def create_access_token(data: dict, expires_delta: timedelta = None): ...
async def get_current_user(token: str = Depends(oauth2_scheme)): ...

# API端点
@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)): ...

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)): ...

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)): ...
```

**测试要点**:
- test_register: 正常注册
- test_register_duplicate: 重复用户名
- test_login: 正常登录
- test_login_wrong_password: 错误密码
- test_get_me: 获取当前用户
- test_protected_route: 受保护路由

**时间估算**: 4-5 小时

---

### 4.2 更新现有API保护

**目标**: 为tasks.py和agents.py添加JWT认证

**实现步骤**:

1. **导入依赖**
   - from api.routes.auth import get_current_user

2. **更新端点签名**
   - 每个端点添加 `current_user: User = Depends(get_current_user)`

3. **测试更新**
   - 测试需要携带JWT Token

**时间估算**: 1 小时

---

### 4.3 agents/coder_agent.py

**目标**: 程序员Agent角色

**实现步骤**:

1. **继承BaseAgent**
   - role = AgentRole.CODER
   - name = "程序员"

2. **系统提示词**
   - 强调代码质量、调试、优化能力
   - 说明可用工具

3. **工具集**
   - [CodeExecuteTool, FileReadTool, FileWriteTool]

**代码结构**:
```python
class CoderAgent(BaseAgent):
    role = AgentRole.CODER
    name = "程序员"
    description = "代码生成和调试专家"
    
    def get_system_prompt(self) -> str: ...
    
    @property
    def tools(self) -> List[BaseTool]: ...
    
    async def execute(self, task: Task, context: str = None) -> AsyncGenerator[AgentStep, None]: ...
```

**时间估算**: 1.5 小时

---

### 4.4 agents/writer_agent.py

**目标**: 作家Agent角色

**实现步骤**:

1. **继承BaseAgent**
   - role = AgentRole.WRITER

2. **系统提示词**
   - 强调文档撰写、内容创作能力

3. **工具集**
   - [SummarizeTool, FileWriteTool]

**时间估算**: 1.5 小时

---

### 4.5 agents/reviewer_agent.py

**目标**: 审查员Agent角色

**实现步骤**:

1. **继承BaseAgent**
   - role = AgentRole.REVIEWER

2. **系统提示词**
   - 强调质量审查、代码审查能力

3. **工具集**
   - [FileReadTool]

**时间估算**: 1.5 小时

---

### 4.6 更新AgentFactory

**目标**: 注册3个新Agent角色

**实现步骤**:

1. **导入新Agent**
   - from agents.coder_agent import CoderAgent
   - from agents.writer_agent import WriterAgent
   - from agents.reviewer_agent import ReviewerAgent

2. **更新_registry**
   - 添加Coder, Writer, Reviewer

**时间估算**: 0.5 小时

**Day 3 总计**: 10-11 小时

---

## 5. Day 4: Memory 系统

### 5.1 core/memory_manager.py

**目标**: 三层记忆管理器

**实现步骤**:

1. **定义MemoryEntry数据类**
   - id, content, memory_type, agent_id, task_id, timestamp, metadata, embedding

2. **初始化向量存储**
   - ChromaDB客户端
   - 创建/获取collection

3. **实现短期记忆操作**
   - add_short_term(content, agent_id)
   - get_short_term(agent_id, limit)
   - clear_short_term(agent_id)
   - 使用deque(maxlen=100)

4. **实现长期记忆操作**
   - add_long_term(content, metadata)
   - search_long_term(query, limit)
   - delete_long_term(memory_id)
   - 使用ChromaDB存储

5. **实现外部记忆操作**
   - add_external(content, source, metadata)
   - search_external(query, limit)
   - 使用ChromaDB存储

6. **实现统一检索**
   - search_all(query, limit)
   - 聚合所有记忆类型的结果

7. **实现向量化**
   - _embed(text)
   - 优先使用LLM embedding
   - Fallback：简单词频向量

**代码结构**:
```python
class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EXTERNAL = "external"

@dataclass
class MemoryEntry:
    id: str
    content: str
    memory_type: MemoryType
    agent_id: Optional[str]
    task_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    embedding: Optional[List[float]]

class MemoryManager:
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        self.short_term: Deque[MemoryEntry] = deque(maxlen=100)
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection("memories")
    
    # 短期记忆
    async def add_short_term(self, content: str, agent_id: str = None) -> None: ...
    async def get_short_term(self, agent_id: str = None, limit: int = 10) -> List[MemoryEntry]: ...
    
    # 长期记忆
    async def add_long_term(self, content: str, metadata: Dict = None) -> str: ...
    async def search_long_term(self, query: str, limit: int = 5) -> List[MemoryEntry]: ...
    
    # 外部记忆
    async def add_external(self, content: str, source: str, metadata: Dict = None) -> str: ...
    async def search_external(self, query: str, limit: int = 5) -> List[MemoryEntry]: ...
    
    # 统一检索
    async def search_all(self, query: str, limit: int = 10) -> List[MemoryEntry]: ...
    
    # 向量化
    async def _embed(self, text: str) -> List[float]: ...
```

**测试要点**:
- test_short_term_memory: 短期记忆CRUD
- test_long_term_memory: 长期记忆存储和检索
- test_external_memory: 外部记忆存储和检索
- test_search_all: 统一检索
- test_embedding: 向量化

**时间估算**: 5-6 小时

---

### 5.2 更新database/models.py

**目标**: 添加MemoryORM表

**实现步骤**:

1. **定义MemoryORM**
   - id, content, memory_type, agent_id, task_id, source, metadata, created_at

2. **更新__init__.py导出**

**时间估算**: 1 小时

**Day 4 总计**: 6-7 小时

---

## 6. Day 5: RAG 系统

### 6.1 core/rag_system.py

**目标**: 文档导入、分块、向量化和检索

**实现步骤**:

1. **定义Document和DocumentChunk数据类**

2. **实现文档导入**
   - import_document(source, doc_type)
   - 支持PDF(PyPDF2), TXT, MD
   - 提取文本内容

3. **实现文本分块**
   - _chunk_text(text, chunk_size=500, overlap=50)
   - 按段落或固定长度切分

4. **实现检索**
   - retrieve(query, limit, filters)
   - 复用MemoryManager.search_external()

5. **实现增强提示生成**
   - augment_prompt(query, context)
   - 将检索结果格式化为上下文

**代码结构**:
```python
@dataclass
class Document:
    id: str
    content: str
    source: str
    doc_type: str
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class DocumentChunk:
    id: str
    doc_id: str
    content: str
    index: int
    embedding: List[float]

class RAGSystem:
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    async def import_document(self, source: str, doc_type: Optional[str] = None) -> Document: ...
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]: ...
    async def retrieve(self, query: str, limit: int = 5, filters: Dict = None) -> List[DocumentChunk]: ...
    async def augment_prompt(self, query: str, context: str = None) -> str: ...
```

**测试要点**:
- test_import_pdf: PDF文档导入
- test_chunk_text: 文本分块
- test_retrieve: 检索功能
- test_augment_prompt: 增强提示生成

**时间估算**: 4-5 小时

---

### 6.2 更新tools/memory_search.py

**目标**: Mock → 真实RAG接入

**实现步骤**:

1. **构造函数接受RAGSystem**
   - __init__(rag_system: RAGSystem)

2. **execute调用RAG检索**
   - results = await rag_system.retrieve(query, limit)
   - 格式化返回结果

**时间估算**: 1 小时

**Day 5 总计**: 5-6 小时

---

## 7. Day 6: Reflection 引擎

### 7.1 core/reflection_engine.py

**目标**: Agent执行后反思和经验学习

**实现步骤**:

1. **定义ReflectionReport数据类**
   - task_id, agent_id, agent_role, success, summary, strengths, weaknesses, suggestions, learned, timestamp

2. **实现reflect方法**
   - 收集任务执行步骤
   - 构建反思提示
   - 调用LLM生成反思报告
   - 提取经验存入长期记忆

3. **实现Agent洞察获取**
   - get_agent_insights(agent_role, limit)
   - 查询长期记忆中的经验

**代码结构**:
```python
@dataclass
class ReflectionReport:
    task_id: str
    agent_id: str
    agent_role: AgentRole
    success: bool
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    suggestions: List[str]
    learned: str
    timestamp: datetime

class ReflectionEngine:
    def __init__(self, llm_router: LLMRouter, memory_manager: MemoryManager):
        self.llm_router = llm_router
        self.memory_manager = memory_manager
    
    async def reflect(self, task_id: str, steps: List[AgentStep], result: TaskResult) -> ReflectionReport: ...
    async def _analyze_steps(self, steps: List[AgentStep]) -> Dict[str, Any]: ...
    async def _generate_report(self, analysis: Dict, result: TaskResult) -> ReflectionReport: ...
    async def _extract_experience(self, report: ReflectionReport) -> str: ...
    async def get_agent_insights(self, agent_role: AgentRole, limit: int = 10) -> List[str]: ...
```

**测试要点**:
- test_reflect_success: 成功任务反思
- test_reflect_failure: 失败任务反思
- test_extract_experience: 经验提取
- test_get_insights: 获取Agent洞察

**时间估算**: 4-5 小时

---

### 7.2 更新core/orchestrator.py

**目标**: 集成Reflection引擎

**实现步骤**:

1. **构造函数接受ReflectionEngine**
   - __init__(..., reflection_engine: Optional[ReflectionEngine] = None)

2. **execute_plan完成后调用反思**
   - 如果reflection_engine存在，生成反思报告

**时间估算**: 1 小时

**Day 6 总计**: 5-6 小时

---

## 8. Day 7: 前端完整功能

### 8.1 页面实现

**目标**: 3个新页面 + 认证Store

**文件清单**:
- `frontend/src/pages/AgentMonitor.tsx` (226行)
- `frontend/src/pages/MultiAgentChat.tsx` (217行)
- `frontend/src/pages/Settings.tsx` (188行)
- `frontend/src/stores/authStore.ts` (100+行)
- `frontend/src/api/client.ts` (更新)

**实现要点**:

1. **AgentMonitor页面**
   - Agent卡片网格（6个角色）
   - 实时状态（SSE）
   - 性能统计

2. **MultiAgentChat页面**
   - 聊天界面
   - Agent选择（多选）
   - Markdown渲染
   - 消息颜色区分

3. **Settings页面**
   - 用户信息
   - LLM配置
   - 主题切换

4. **authStore**
   - login/register/logout
   - Token管理
   - 错误处理

**时间估算**: 8-10 小时

**Day 7 总计**: 8-10 小时

---

## 9. Day 8: 联调 + 性能优化

### 9.1 端到端场景测试

**场景1**：编程任务
```python
# 测试脚本
async def test_coding_task():
    # 1. 创建任务
    task = await create_task("写一个Python函数计算斐波那契数列")
    
    # 2. 执行
    result = await orchestrator.execute_plan(plan)
    
    # 3. 验证
    assert result.status == "completed"
    assert "def fibonacci" in result.output
```

**场景2**：知识库问答
**场景3**：多Agent协作

**时间估算**: 3-4 小时

---

### 9.2 API限流

**目标**: 实现RateLimitMiddleware

**实现步骤**:

1. **实现MemoryRateLimiter**
   - 单实例内存版
   - 滑动窗口计数

2. **注册中间件**
   - app.add_middleware(RateLimitMiddleware)

**时间估算**: 1.5 小时

---

### 9.3 性能优化

**优化项**:
- 数据库索引：tasks.status, tasks.created_at, steps.task_id
- ChromaDB批量插入
- LLM并发控制：Semaphore(5)
- 前端代码分割

**性能指标验证**:
- API响应时间 < 500ms
- 前端首屏 < 2s

**时间估算**: 2-3 小时

**Day 8 总计**: 6-8.5 小时

---

## 10. 并行执行建议

### 10.1 可并行的任务

**Day 1-2期间**:
- 4个核心工具可并行开发（互不依赖）
- 2个补充工具可并行

**Day 3-4期间**:
- JWT认证和Agent角色可并行
- Memory系统和前端认证Store可并行

**Day 5-6期间**:
- RAG和Reflection部分并行（都依赖Memory）

**Day 7-8期间**:
- 前端页面可并行开发
- 联调和性能优化串行

### 10.2 分组建议

如果有多人协作：

**组A（后端核心）**:
- Day 1-2: 工具实现
- Day 3: JWT认证
- Day 4-5: Memory + RAG
- Day 6: Reflection

**组B（Agent + 前端）**:
- Day 3: 3个新Agent
- Day 7: 前端页面
- Day 8: 前端联调

**组C（测试 + DevOps）**:
- Day 2: 工具测试
- Day 4-8: 持续测试
- Day 8: 性能优化

---

## 11. 风险缓解

| 风险 | 可能性 | 影响 | 缓解措施 | 责任人 |
|------|--------|------|---------|--------|
| CodeExecuteTool安全性 | 高 | 高 | 多层安全（AST+子进程+超时） | Day 1 |
| ChromaDB性能 | 中 | 中 | 批量插入、索引优化 | Day 4-5 |
| LLM Embedding成本 | 中 | 低 | 本地模型fallback、缓存 | Day 4 |
| 前端认证复杂度 | 中 | 中 | 使用成熟库（axios拦截器） | Day 3,7 |
| JWT密钥泄露 | 低 | 高 | 环境变量配置、定期轮换 | Day 3 |
| RAG检索质量 | 中 | 中 | 调优分块大小、重排序 | Day 5 |

---

## 附录 A: 完整文件清单

### Day 1
- `tools/code_execute.py` (150-200行)
- `tools/file_io.py` (100-150行)
- `tools/summarize.py` (80-120行)
- `tools/agent_message.py` (80-120行)

### Day 2
- `tools/memory_search.py` (50-80行，Mock)
- `tools/web_browser.py` (100-150行)
- `tools/web_search.py` (更新，50-80行)
- `tests/unit/test_code_execute.py` (150-200行)
- `tests/unit/test_file_io.py` (100-150行)
- `tests/unit/test_summarize.py` (80-120行)
- `tests/unit/test_agent_message.py` (80-120行)

### Day 3
- `api/routes/auth.py` (200-250行)
- `database/models.py` (更新，+30行)
- `agents/coder_agent.py` (100-150行)
- `agents/writer_agent.py` (100-150行)
- `agents/reviewer_agent.py` (100-150行)
- `agents/factory.py` (更新，+10行)
- `tests/unit/test_auth.py` (150-200行)

### Day 4
- `core/memory_manager.py` (250-300行)
- `database/models.py` (更新，+20行)
- `tests/unit/test_memory_manager.py` (200-250行)

### Day 5
- `core/rag_system.py` (200-250行)
- `tools/memory_search.py` (更新，+30行)
- `tests/unit/test_rag_system.py` (150-200行)

### Day 6
- `core/reflection_engine.py` (200-250行)
- `core/orchestrator.py` (更新，+20行)
- `tests/unit/test_reflection_engine.py` (150-200行)

### Day 7
- `frontend/src/pages/AgentMonitor.tsx` (200-250行)
- `frontend/src/pages/MultiAgentChat.tsx` (200-250行)
- `frontend/src/pages/Settings.tsx` (150-200行)
- `frontend/src/stores/authStore.ts` (100-150行)
- `frontend/src/api/client.ts` (更新，+50行)

### Day 8
- `api/middleware/rate_limit.py` (100-150行)
- `tests/integration/test_week3.py` (300-400行)

**总计**: ~35个文件，~5000-6000行代码

---

## 附录 B: 依赖检查

### 后端新增依赖
```
# 已在requirements.txt
PyPDF2==3.0.1              # PDF解析
beautifulsoup4==4.12.2     # HTML解析
duckduckgo-search==3.9.6   # Web搜索
chromadb==0.4.18           # 向量数据库
python-jose[cryptography]==3.3.0  # JWT
passlib[bcrypt]==1.7.4     # 密码哈希
```

### 前端依赖（Week 2已安装）
```
react-router-dom
zustand
axios
lucide-react
```

---

> **实施计划结束**
> 
> 下一步：开始按 Day 1 → Day 8 顺序编码实现，或按并行建议分组执行
