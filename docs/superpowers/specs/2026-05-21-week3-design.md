# Week 3 设计文档：高级功能 + 完整体验

> **版本**: 1.0
> **日期**: 2026-05-21
> **基于**: Week 2 完成的基础设施 + 核心引擎
> **目标**: 实现高级功能（RAG、Memory、Reflection）+ 完整用户体验
> **核心原则**: Memory先于RAG（复用向量存储）、JWT认证提前（保护API）

---

## 目录

1. [概述](#1-概述)
2. [Day 1: 核心 MCP 工具](#2-day-1-核心-mcp-工具)
3. [Day 2: 补充工具 + 测试](#3-day-2-补充工具--测试)
4. [Day 3: JWT 认证 + 新 Agent 角色](#4-day-3-jwt-认证--新-agent-角色)
5. [Day 4: Memory 系统](#5-day-4-memory-系统)
6. [Day 5: RAG 系统](#6-day-5-rag-系统)
7. [Day 6: Reflection 引擎](#7-day-6-reflection-引擎)
8. [Day 7: 前端完整功能](#8-day-7-前端完整功能)
9. [Day 8: 联调 + 性能优化](#9-day-8-联调--性能优化)
10. [API 设计](#10-api-设计)
11. [测试策略](#11-测试策略)
12. [验收标准](#12-验收标准)
13. [风险缓解](#13-风险缓解)

---

## 1. 概述

### 1.1 Week 3 目标

在 Week 2 基础设施之上，构建高级功能：

- **6 个 MCP 工具**（CodeExecute, FileIO, Summarize, AgentMessage, MemorySearch, WebBrowser）
- **3 个新 Agent 角色**（Coder, Writer, Reviewer）
- **JWT 认证**（提前保护所有 API）
- **Memory 系统**（三层记忆：短期/长期/外部）
- **RAG 系统**（复用 Memory 的向量存储）
- **Reflection 引擎**（执行后反思 + 经验学习）
- **前端完整功能**（AgentMonitor, Chat, Settings）
- **API 限流**（Rate Limiting）

### 1.2 关键设计决策

| 决策 | 说明 |
|------|------|
| **Memory先于RAG** | Memory实现向量存储基础设施，RAG复用，避免重复代码 |
| **JWT提前到Day 3** | 后续所有API开发都有认证保护，前端统一处理Token |
| **6个工具而非8个** | 质量优先，WebSearch和Calculator已在Week 2实现 |
| **AgentMessage工具** | 封装A2A Bus，让Agent通过工具调用发送消息 |

### 1.3 与 Week 2 的衔接

```
Week 2 基础:
├── core/planner.py         → Week 3 Reflection分析规划质量
├── core/orchestrator.py    → Week 3 Reflection分析执行过程
├── core/a2a_bus.py         → Week 3 AgentMessage工具封装
├── agents/*_agent.py       → Week 3 补充3个角色
├── tools/web_search.py     → Week 3 真实化（DuckDuckGo）
├── tools/calculator.py     → Week 3 保持
├── api/routes/*.py         → Week 3 增加JWT保护
└── frontend/               → Week 3 补充页面

Week 3 新增:
├── tools/code_execute.py   # 代码执行沙箱
├── tools/file_io.py        # 文件读写
├── tools/summarize.py      # 文本摘要
├── tools/agent_message.py  # Agent通信工具
├── tools/memory_search.py  # 记忆检索
├── tools/web_browser.py    # 网页浏览
├── agents/coder_agent.py   # 程序员
├── agents/writer_agent.py  # 作家
├── agents/reviewer_agent.py # 审查员
├── api/routes/auth.py      # JWT认证
├── core/memory_manager.py  # 三层记忆
├── core/rag_system.py      # RAG检索
├── core/reflection_engine.py # 反思引擎
└── frontend/pages/         # AgentMonitor, Chat, Settings
```

---

## 2. Day 1: 核心 MCP 工具

### 2.1 工具实现优先级

**高优先级（4个）**：

| 工具 | 复杂度 | 面试亮点 | 说明 |
|------|--------|---------|------|
| **CodeExecuteTool** | 高 | ⭐⭐⭐ | 安全沙箱执行Python代码 |
| **FileIOTool** | 低 | ⭐ | 文件读写操作 |
| **SummarizeTool** | 中 | ⭐⭐ | 长文本摘要 |
| **AgentMessageTool** | 中 | ⭐⭐ | Agent间通信封装 |

### 2.2 CodeExecuteTool（代码执行沙箱）

**文件**: `tools/code_execute.py`

**安全设计**：
```python
class CodeExecuteTool(BaseTool):
    """安全代码执行工具
    
    在受限环境中执行Python代码，禁止危险操作。
    """
    name = "code_execute"
    description = "安全执行Python代码并返回结果"
    
    # 禁止的模块和函数
    _FORBIDDEN_MODULES = ['os', 'sys', 'subprocess', 'socket', 'requests']
    _FORBIDDEN_FUNCTIONS = ['eval', 'exec', 'compile', '__import__']
    
    async def execute(self, code: str, timeout: int = 30) -> str:
        """执行代码
        
        流程:
        1. 代码安全扫描（禁止模块/函数）
        2. 在子进程中执行（隔离）
        3. 捕获stdout/stderr
        4. 超时控制
        5. 返回结果或错误
        """
```

**安全措施**：

```python
# 安全策略配置
FORBIDDEN_MODULES = {'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests'}
FORBIDDEN_FUNCTIONS = {'eval', 'exec', 'compile', '__import__', 'open'}

class CodeExecuteTool(BaseTool):
    async def execute(self, code: str, timeout: int = 30) -> str:
        # 1. AST静态扫描
        if not self._is_safe_code(code):
            return "错误：代码包含禁止的模块或函数"
        
        # 2. 子进程隔离执行
        result = await self._run_in_subprocess(code, timeout)
        
        # 3. 输出截断（最大10000字符）
        return result[:10000]
    
    def _is_safe_code(self, code: str) -> bool:
        """AST扫描检查禁止代码"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # 检查import
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name in FORBIDDEN_MODULES:
                            return False
                # 检查函数调用
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in FORBIDDEN_FUNCTIONS:
                            return False
            return True
        except SyntaxError:
            return False
    
    async def _run_in_subprocess(self, code: str, timeout: int) -> str:
        """在子进程中执行代码"""
        import subprocess
        result = subprocess.run(
            ['python', '-c', code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd='./workspace'  # 限制工作目录
        )
        return result.stdout + result.stderr
```

**示例**：
```python
# 用户输入
code = """
numbers = [1, 2, 3, 4, 5]
sum_result = sum(numbers)
print(f"Sum: {sum_result}")
"""

# 工具执行
result = await tool.execute(code)
# 返回: "Sum: 15\n"
```

---

### 2.3 FileIOTool（文件读写）

**文件**: `tools/file_io.py`

```python
class FileReadTool(BaseTool):
    """文件读取工具"""
    name = "file_read"
    description = "读取文件内容"
    
    async def execute(self, path: str, limit: int = 1000) -> str:
        """读取文件，返回前limit行"""

class FileWriteTool(BaseTool):
    """文件写入工具"""
    name = "file_write"
    description = "写入内容到文件"
    
    async def execute(self, path: str, content: str) -> str:
        """写入文件，返回成功信息"""
```

**安全限制**：

```python
from pathlib import Path

ALLOWED_DIR = Path("./workspace").resolve()
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

class FileReadTool(BaseTool):
    def _sanitize_path(self, path: str) -> Path:
        """确保路径在允许目录内"""
        target = (ALLOWED_DIR / path).resolve()
        if not str(target).startswith(str(ALLOWED_DIR)):
            raise ValueError(f"路径超出允许范围: {path}")
        return target
    
    async def execute(self, path: str, limit: int = 1000) -> str:
        safe_path = self._sanitize_path(path)
        
        # 检查文件大小
        if safe_path.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(f"文件超过大小限制: {MAX_FILE_SIZE} bytes")
        
        with open(safe_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()[:limit]
        return ''.join(lines)

class FileWriteTool(BaseTool):
    async def execute(self, path: str, content: str) -> str:
        safe_path = self._sanitize_path(path)
        
        # 检查内容大小
        if len(content.encode('utf-8')) > MAX_FILE_SIZE:
            raise ValueError(f"内容超过大小限制: {MAX_FILE_SIZE} bytes")
        
        # 确保父目录存在
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"文件已写入: {safe_path}"
```

---

### 2.4 SummarizeTool（文本摘要）

**文件**: `tools/summarize.py`

```python
class SummarizeTool(BaseTool):
    """文本摘要工具
    
    使用LLM对长文本进行摘要。
    """
    name = "summarize"
    description = "对长文本进行摘要"
    
    async def execute(self, text: str, max_length: int = 200) -> str:
        """摘要文本
        
        流程:
        1. 检查文本长度（超过阈值才摘要）
        2. 调用LLM进行摘要
        3. 返回摘要结果
        """
```

**优化策略**：
- 短文本（<500字）直接返回，不摘要
- 长文本分段摘要，再合并
- 支持指定摘要长度和风格（简洁/详细）

---

### 2.5 AgentMessageTool（Agent通信）

**文件**: `tools/agent_message.py`

```python
class AgentMessageTool(BaseTool):
    """Agent消息发送工具
    
    封装A2A Bus，让Agent可以通过工具调用发送消息给其他Agent。
    """
    name = "agent_message"
    description = "发送消息给其他Agent"
    
    def __init__(self, a2a_bus: A2ABus):
        self.a2a_bus = a2a_bus
    
    async def execute(self, receiver_role: str, message: str) -> str:
        """发送消息
        
        流程:
        1. 查找receiver_role对应的Agent
        2. 构造A2AMessage
        3. 通过A2A Bus发送
        4. 等待响应（可选）
        5. 返回发送结果
        """
```

**设计意义**：
- 让Agent可以通过ReAct循环自然地"调用"通信
- 不需要直接操作A2A Bus，通过工具抽象
- 可以在系统提示中描述通信能力

---

## 3. Day 2: 补充工具 + 测试

### 3.1 MemorySearchTool（记忆检索）

**文件**: `tools/memory_search.py`

```python
class MemorySearchTool(BaseTool):
    """记忆检索工具
    
    检索历史任务记忆和知识库。
    Week 3 Day 2先实现mock版本，Day 5接入真实RAG。
    """
    name = "memory_search"
    description = "搜索历史记忆和知识库"
    
    async def execute(self, query: str, limit: int = 5) -> str:
        """搜索记忆
        
        Day 2: Mock实现，返回固定结果
        Day 5: 接入真实RAG系统
        """
```

**Day 2实现**：Mock版本，返回预设记忆片段
**Day 5更新**：接入core/rag_system.py，真实检索

---

### 3.2 WebBrowserTool（网页浏览）

**文件**: `tools/web_browser.py`

```python
class WebBrowserTool(BaseTool):
    """网页浏览工具
    
    抓取网页内容并提取文本。
    """
    name = "web_browser"
    description = "浏览网页并提取内容"
    
    async def execute(self, url: str) -> str:
        """浏览网页
        
        流程:
        1. 发送HTTP GET请求
        2. 解析HTML
        3. 提取正文文本（去除广告/导航）
        4. 返回提取的文本
        """
```

**依赖**：httpx, beautifulsoup4

---

### 3.3 WebSearchTool真实化

**文件**: `tools/web_search.py`（更新）

将Week 2的Mock版本替换为真实实现：

```python
class WebSearchTool(BaseTool):
    """真实Web搜索工具
    
    使用DuckDuckGo搜索API。
    """
    
    async def execute(self, query: str, max_results: int = 5) -> str:
        """搜索并返回结果摘要"""
        # 调用duckduckgo-search库
        # 返回格式化的搜索结果
```

---

### 3.4 工具测试

**测试文件**: `tests/unit/test_tools.py`

覆盖所有6个新工具：
- test_code_execute_safe: 安全代码执行
- test_code_execute_forbidden: 禁止代码检测
- test_file_read: 文件读取
- test_file_write: 文件写入
- test_summarize: 文本摘要
- test_agent_message: Agent消息
- test_memory_search: 记忆检索
- test_web_browser: 网页浏览

---

## 4. Day 3: JWT 认证 + 新 Agent 角色

### 4.1 JWT 认证（上午）

**文件**: `api/routes/auth.py`

**Pydantic模型**：
```python
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
```

**端点**：
```python
@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest): ...

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest): ...

@router.get("/me", response_model=UserResponse)
async def get_current_user(user: User = Depends(get_current_user)): ...
```

**JWT实现**：
- 使用`python-jose`生成/验证JWT
- 使用`passlib[bcrypt]`密码哈希
- Token有效期：24小时
- 依赖注入：`get_current_user`验证Token

**数据库模型更新**：
```python
class UserORM(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=...)
```

---

### 4.2 保护现有API（上午）

**更新** `api/routes/tasks.py` 和 `api/routes/agents.py`：

```python
from api.routes.auth import get_current_user

@router.post("/", response_model=TaskResponse)
async def create_task(
    request: CreateTaskRequest,
    user: User = Depends(get_current_user),  # 添加认证
    db: AsyncSession = Depends(get_db)
):
    # ...
```

---

### 4.3 新 Agent 角色（下午）

**文件**: 
- `agents/coder_agent.py`
- `agents/writer_agent.py`
- `agents/reviewer_agent.py`

#### CoderAgent（程序员）

```python
class CoderAgent(BaseAgent):
    role = AgentRole.CODER
    name = "程序员"
    description = "代码生成和调试专家"
    
    def get_system_prompt(self) -> str:
        return """你是一个资深程序员，擅长：
        - 编写高质量、可维护的代码
        - 代码审查和优化建议
        - 调试和错误修复
        - 技术方案设计
        
        使用code_execute工具测试代码。
        使用file_read/file_write工具读写文件。
        """
    
    @property
    def tools(self) -> List[BaseTool]:
        return [CodeExecuteTool(), FileReadTool(), FileWriteTool()]
```

#### WriterAgent（作家）

```python
class WriterAgent(BaseAgent):
    role = AgentRole.WRITER
    name = "作家"
    description = "文档撰写和内容创作专家"
    
    def get_system_prompt(self) -> str:
        return """你是一个专业作家，擅长：
        - 技术文档撰写
        - 内容创作和润色
        - 长文本摘要
        - 多语言翻译
        
        使用summarize工具处理长文本。
        使用file_write工具保存文档。
        """
    
    @property
    def tools(self) -> List[BaseTool]:
        return [SummarizeTool(), FileWriteTool()]
```

#### ReviewerAgent（审查员）

```python
class ReviewerAgent(BaseAgent):
    role = AgentRole.REVIEWER
    name = "审查员"
    description = "质量审查和代码审查专家"
    
    def get_system_prompt(self) -> str:
        return """你是一个严格的质量审查员，擅长：
        - 代码审查（风格、安全、性能）
        - 文档质量检查
        - 逻辑一致性验证
        - 提供改进建议
        
        使用file_read工具读取待审查内容。
        提供详细的审查报告。
        """
    
    @property
    def tools(self) -> List[BaseTool]:
        return [FileReadTool()]
```

---

### 4.4 更新 AgentFactory

**更新** `agents/factory.py`：

```python
class AgentFactory:
    _registry: Dict[AgentRole, Type[BaseAgent]] = {
        AgentRole.EXECUTOR: ExecutorAgent,
        AgentRole.RESEARCHER: ResearcherAgent,
        AgentRole.PLANNER: PlannerAgent,
        AgentRole.CODER: CoderAgent,      # 新增
        AgentRole.WRITER: WriterAgent,    # 新增
        AgentRole.REVIEWER: ReviewerAgent, # 新增
    }
```

---

## 5. Day 4: Memory 系统

### 5.1 设计目标

实现三层记忆系统：

| 记忆类型 | 存储介质 | 容量 | 持久化 | 用途 |
|----------|----------|------|--------|------|
| **短期记忆** | 内存/Redis | 小（最近N条） | 否 | 当前任务上下文 |
| **长期记忆** | ChromaDB | 大 | 是 | 历史任务经验 |
| **外部记忆** | 文件/数据库 | 无限 | 是 | 知识库、文档 |

### 5.2 核心类设计

**文件**: `core/memory_manager.py`

```python
class MemoryType(str, Enum):
    SHORT_TERM = "short_term"    # 短期记忆
    LONG_TERM = "long_term"      # 长期记忆
    EXTERNAL = "external"        # 外部记忆

class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    memory_type: MemoryType
    agent_id: Optional[str]
    task_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    embedding: Optional[List[float]]  # 向量嵌入

class MemoryManager:
    """记忆管理器
    
    统一管理三层记忆，提供统一的CRUD和检索接口。
    """
    
    def __init__(self, llm_router: LLMRouter):
        self.llm_router = llm_router
        self.short_term: Deque[MemoryEntry] = deque(maxlen=100)
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection("memories")
    
    # 短期记忆操作
    async def add_short_term(self, content: str, agent_id: str = None) -> None: ...
    async def get_short_term(self, agent_id: str = None, limit: int = 10) -> List[MemoryEntry]: ...
    async def clear_short_term(self, agent_id: str = None) -> None: ...
    
    # 长期记忆操作（向量存储）
    async def add_long_term(self, content: str, metadata: Dict = None) -> str: ...
    async def search_long_term(self, query: str, limit: int = 5) -> List[MemoryEntry]: ...
    async def delete_long_term(self, memory_id: str) -> None: ...
    
    # 外部记忆操作
    async def add_external(self, content: str, source: str, metadata: Dict = None) -> str: ...
    async def search_external(self, query: str, limit: int = 5) -> List[MemoryEntry]: ...
    
    # 统一检索（跨所有记忆类型）
    async def search_all(self, query: str, limit: int = 10) -> List[MemoryEntry]: ...
    
    # 向量化
    async def _embed(self, text: str) -> List[float]: ...
```

### 5.3 数据库模型更新

**更新** `database/models.py`：

```python
class MemoryORM(Base):
    """长期记忆表（向量存储的元数据）"""
    __tablename__ = "memories"
    
    id: Mapped[str] = mapped_column(String, primary_key=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    memory_type: Mapped[str] = mapped_column(String, nullable=False)  # long_term / external
    agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    task_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=...)
```

### 5.4 向量化实现

```python
async def _embed(self, text: str) -> List[float]:
    """文本向量化
    
    使用LLM的embedding接口（如OpenAI的text-embedding-ada-002）。
    如果没有配置，使用简单的TF-IDF作为fallback。
    """
    # 优先使用LLM embedding
    # Fallback: 简单的词频向量
```

---

## 6. Day 5: RAG 系统

### 6.1 设计原则

**复用Memory系统的向量存储**：
- RAG使用MemoryManager的`search_long_term`和`search_external`
- 文档导入时通过`add_external`存入外部记忆
- 检索时统一通过MemoryManager搜索

### 6.2 核心类设计

**文件**: `core/rag_system.py`

```python
class Document:
    """文档"""
    id: str
    content: str
    source: str  # 文件路径或URL
    doc_type: str  # pdf, txt, md, html
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    created_at: datetime

class DocumentChunk:
    """文档分块"""
    id: str
    doc_id: str
    content: str
    index: int  # 在原文中的位置
    embedding: List[float]

class RAGSystem:
    """RAG检索增强系统
    
    提供文档导入、分块、向量化和检索功能。
    复用MemoryManager的向量存储。
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    # 文档导入
    async def import_document(
        self,
        source: str,  # 文件路径或URL
        doc_type: Optional[str] = None
    ) -> Document: ...
    
    # 文本分块
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]: ...
    
    # 检索（复用MemoryManager）
    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        filters: Dict[str, Any] = None
    ) -> List[DocumentChunk]: ...
    
    # 生成增强提示
    async def augment_prompt(
        self,
        query: str,
        context: str = None
    ) -> str: ...
```

### 6.3 文档导入流程

```
用户上传PDF
  → RAGSystem.import_document("/path/to/doc.pdf")
    → 读取PDF内容（PyPDF2）
    → 文本分块（chunk_size=500, overlap=50）
    → 每个分块向量化
    → 存入MemoryManager（外部记忆）
    → 返回Document对象
```

### 6.4 检索流程

```
用户查询: "Python asyncio最佳实践"
  → RAGSystem.retrieve("Python asyncio最佳实践")
    → MemoryManager.search_external(query)
      → 查询向量化
      → ChromaDB相似度搜索
      → 返回最相关的DocumentChunk列表
```

### 6.5 更新MemorySearchTool

**更新** `tools/memory_search.py`（Day 2 Mock → Day 5 真实）：

```python
class MemorySearchTool(BaseTool):
    """真实记忆检索工具
    
    接入RAGSystem，支持搜索历史记忆和知识库。
    """
    
    def __init__(self, rag_system: RAGSystem):
        self.rag_system = rag_system
    
    async def execute(self, query: str, limit: int = 5) -> str:
        """搜索记忆和知识库"""
        results = await self.rag_system.retrieve(query, limit)
        return self._format_results(results)
```

---

## 7. Day 6: Reflection 引擎

### 7.1 设计目标

让Agent能够：
1. **执行后反思**：分析任务执行过程，总结成功/失败原因
2. **经验提取**：将反思结果转化为可复用的经验
3. **性能优化**：根据经验改进后续执行策略

### 7.2 核心类设计

**文件**: `core/reflection_engine.py`

```python
class ReflectionReport:
    """反思报告"""
    task_id: str
    agent_id: str
    agent_role: AgentRole
    success: bool
    summary: str  # 执行总结
    strengths: List[str]  # 做得好的地方
    weaknesses: List[str]  # 需要改进的地方
    suggestions: List[str]  # 改进建议
    learned: str  # 学到的东西
    timestamp: datetime

class ReflectionEngine:
    """反思引擎
    
    分析Agent执行任务的历史，生成反思报告和经验。
    """
    
    def __init__(self, llm_router: LLMRouter, memory_manager: MemoryManager):
        self.llm_router = llm_router
        self.memory_manager = memory_manager
    
    async def reflect(
        self,
        task_id: str,
        steps: List[AgentStep],
        result: TaskResult
    ) -> ReflectionReport:
        """对任务执行进行反思
        
        流程:
        1. 收集任务执行步骤
        2. 分析成功/失败原因
        3. 生成反思报告
        4. 提取经验存入长期记忆
        """
    
    async def _analyze_steps(self, steps: List[AgentStep]) -> Dict[str, Any]: ...
    async def _generate_report(self, analysis: Dict, result: TaskResult) -> ReflectionReport: ...
    async def _extract_experience(self, report: ReflectionReport) -> str: ...
    
    async def get_agent_insights(self, agent_role: AgentRole, limit: int = 10) -> List[str]:
        """获取某个Agent角色的经验总结"""
```

### 7.3 反思提示模板

```python
REFLECTION_PROMPT = """
你是一个任务执行分析专家。请分析以下任务执行过程，生成反思报告。

任务信息:
- 任务ID: {task_id}
- Agent角色: {agent_role}
- 执行结果: {success}

执行步骤:
{steps_description}

最终输出:
{output}

请按以下格式输出反思报告:

## 执行总结
（简要总结任务执行情况）

## 做得好的地方
- （列出2-3个优点）

## 需要改进的地方
- （列出2-3个不足）

## 改进建议
- （列出2-3条具体建议）

## 学到的东西
（用1-2句话总结学到的经验）
"""
```

### 7.4 与Orchestrator集成

**更新** `core/orchestrator.py`：

```python
class Orchestrator:
    def __init__(self, ..., reflection_engine: Optional[ReflectionEngine] = None):
        self.reflection_engine = reflection_engine
    
    async def execute_plan(self, plan, ...):
        # ... 执行计划 ...
        
        # 执行完成后进行反思
        if self.reflection_engine:
            report = await self.reflection_engine.reflect(
                task_id=task.id,
                steps=all_steps,
                result=result
            )
            logger.info(f"反思报告生成: {report.summary}")
        
        yield result
```

---

## 8. Day 7: 前端完整功能

### 8.1 新增页面

| 页面 | 路由 | 功能 |
|------|------|------|
| **AgentMonitor** | `/agents` | Agent实时状态监控 |
| **MultiAgentChat** | `/chat` | 多Agent协作聊天室 |
| **Settings** | `/settings` | 系统设置和个人信息 |

### 8.2 AgentMonitor页面

**文件**: `frontend/src/pages/AgentMonitor.tsx`

**功能**：
- Agent卡片网格（6个角色）
- 每个卡片显示：角色、状态、当前任务、性能统计
- 实时状态更新（SSE）
- 点击查看Agent详情和反思报告

```typescript
interface AgentCardProps {
  agent: {
    id: string;
    role: string;
    name: string;
    status: 'idle' | 'busy' | 'error';
    currentTask: string | null;
    completedTasks: number;
    successRate: number;
  };
}
```

### 8.3 MultiAgentChat页面

**文件**: `frontend/src/pages/MultiAgentChat.tsx`

**功能**：
- 聊天界面（类似ChatGPT）
- 左侧：Agent选择（可多选）
- 右侧：消息列表
- 支持Markdown渲染
- 显示Agent正在输入状态
- 消息按角色颜色区分

```typescript
interface ChatMessage {
  id: string;
  sender: 'user' | AgentRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}
```

### 8.4 Settings页面

**文件**: `frontend/src/pages/Settings.tsx`

**功能**：
- 用户信息（只读）
- LLM配置（API Key、模型选择）
- 主题切换（亮色/暗色）
- 语言设置
- 关于信息

### 8.5 前端认证集成

**更新** `src/api/client.ts`：

```typescript
// 添加请求拦截器，自动附加JWT Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 登录/登出方法
export const authAPI = {
  login: (username: string, password: string) => ...,
  register: (username: string, password: string) => ...,
  logout: () => localStorage.removeItem('token'),
};
```

**新增** `src/stores/authStore.ts`：

```typescript
interface User {
  id: string;
  username: string;
  email?: string;
  created_at: string;
}

interface AuthStore {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // 认证操作
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email?: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
  
  // 工具函数
  getToken: () => string | null;
  setToken: (token: string) => void;
}

// 使用示例
const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  
  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authAPI.login(username, password);
      localStorage.setItem('token', response.access_token);
      set({ user: response.user, isAuthenticated: true });
    } catch (error) {
      set({ error: error.message });
    } finally {
      set({ isLoading: false });
    }
  },
  
  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, isAuthenticated: false });
  },
  
  checkAuth: async () => {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
      const user = await authAPI.getCurrentUser();
      set({ user, isAuthenticated: true });
    } catch {
      localStorage.removeItem('token');
    }
  },
  
  clearError: () => set({ error: null }),
  getToken: () => localStorage.getItem('token'),
  setToken: (token) => localStorage.setItem('token', token),
}));
```

---

## 9. Day 8: 联调 + 性能优化

### 9.1 端到端场景测试

**场景1**：编程任务（CoderAgent）
```
用户: "写一个Python函数，计算斐波那契数列"
→ Planner拆解: [设计算法, 编写代码, 测试代码]
→ CoderAgent执行:
  1. 思考算法
  2. 编写代码（FileWriteTool）
  3. 测试代码（CodeExecuteTool）
→ 返回结果 + Reflection报告
```

**场景2**：写作任务（WriterAgent）
```
用户: "写一篇关于Python异步编程的技术博客"
→ ResearcherAgent搜索资料
→ WriterAgent撰写
→ ReviewerAgent审查
→ 返回最终文档
```

**场景3**：研究任务（Researcher + RAG）
```
用户: "基于知识库，总结Python最佳实践"
→ RAG检索知识库
→ ResearcherAgent分析
→ SummarizeTool生成摘要
→ 返回总结报告
```

### 9.2 API限流

**文件**: `api/middleware/rate_limit.py`

**方案A：Redis版（推荐，多实例部署）**
```python
class RedisRateLimiter:
    """基于Redis的令牌桶限流"""
    
    def __init__(self, redis_client, requests_per_minute: int = 60):
        self.redis = redis_client
        self.rpm = requests_per_minute
    
    async def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        # 使用Redis实现令牌桶
        ...
```

**方案B：内存版（备选，单实例部署）**
```python
class MemoryRateLimiter:
    """内存版限流（适用于单实例开发/测试）"""
    
    _storage: Dict[str, List[float]] = {}  # key: [timestamp1, timestamp2, ...]
    
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.window = 60  # 60秒窗口
    
    async def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self._storage:
            self._storage[key] = []
        
        # 清理过期时间戳
        self._storage[key] = [t for t in self._storage[key] if now - t < self.window]
        
        # 检查是否超过限制
        if len(self._storage[key]) >= self.rpm:
            return False
        
        self._storage[key].append(now)
        return True
```

**使用方式**：
```python
# 根据环境选择实现
if settings.REDIS_URL:
    limiter = RedisRateLimiter(redis_client)
else:
    limiter = MemoryRateLimiter()

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    if not await limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "请求过于频繁，请稍后再试"}
        )
    return await call_next(request)
```

### 9.3 性能优化清单

**性能指标目标**：
| 指标 | 目标值 | 测量方式 |
|------|--------|----------|
| API响应时间（P95） | < 500ms | 端到端测试 |
| 前端首屏加载 | < 2s | Lighthouse |
| LLM调用并发 | <= 5 | 配置控制 |
| 数据库查询 | < 100ms | 慢查询日志 |
| 内存使用 | < 2GB | 监控 |

**优化项**：
- [ ] 数据库查询优化（添加索引：tasks.status, tasks.created_at, steps.task_id）
- [ ] ChromaDB批量插入（避免逐条插入）
- [ ] LLM调用并发控制（Semaphore(5)）
- [ ] 前端代码分割（Code Splitting，按路由懒加载）
- [ ] 图片/资源懒加载
- [ ] API响应缓存（Redis，缓存热点数据）

---

## 10. API 设计

### 10.1 新增API端点

**认证API** (`/api/v1/auth`)：
```
POST   /api/v1/auth/register       # 注册
POST   /api/v1/auth/login          # 登录
GET    /api/v1/auth/me             # 获取当前用户
POST   /api/v1/auth/refresh        # 刷新Token
```

**知识库API** (`/api/v1/knowledge`)：
```
POST   /api/v1/knowledge/documents  # 上传文档
GET    /api/v1/knowledge/documents  # 列出文档
DELETE /api/v1/knowledge/documents/{id} # 删除文档
POST   /api/v1/knowledge/search    # 搜索知识库
```

**Memory API** (`/api/v1/memory`)：
```
POST   /api/v1/memory              # 添加记忆
GET    /api/v1/memory              # 查询记忆
DELETE /api/v1/memory/{id}         # 删除记忆
```

**Reflection API** (`/api/v1/reflections`)：
```
GET    /api/v1/reflections         # 获取反思报告列表
GET    /api/v1/reflections/{id}    # 获取单个报告
```

### 10.2 受保护的API

所有现有API（`/api/v1/tasks`, `/api/v1/agents`）添加JWT认证：
```python
@router.get("/")
async def list_tasks(
    user: User = Depends(get_current_user),  # 新增
    db: AsyncSession = Depends(get_db)
):
    ...
```

---

## 11. 测试策略

### 11.1 单元测试

| 模块 | 测试文件 | 关键测试点 |
|------|---------|-----------|
| CodeExecuteTool | `test_code_execute.py` | 安全执行、禁止代码检测、超时 |
| FileIOTool | `test_file_io.py` | 读写文件、路径限制 |
| SummarizeTool | `test_summarize.py` | 摘要质量、短文本处理 |
| AgentMessageTool | `test_agent_message.py` | 消息发送、接收 |
| MemorySearchTool | `test_memory_search.py` | Mock检索、真实检索 |
| WebBrowserTool | `test_web_browser.py` | 网页抓取、HTML解析 |
| CoderAgent | `test_coder_agent.py` | 代码生成、工具使用 |
| WriterAgent | `test_writer_agent.py` | 文档撰写、摘要 |
| ReviewerAgent | `test_reviewer_agent.py` | 审查逻辑 |
| MemoryManager | `test_memory_manager.py` | 三层记忆CRUD、检索 |
| RAGSystem | `test_rag_system.py` | 文档导入、分块、检索 |
| ReflectionEngine | `test_reflection_engine.py` | 反思报告生成 |
| Auth | `test_auth.py` | 注册、登录、Token验证 |

### 11.2 集成测试

| 场景 | 测试内容 |
|------|---------|
| 编程任务 | Planner → CoderAgent → CodeExecute → FileWrite |
| 写作任务 | Researcher → Writer → Reviewer |
| RAG检索 | 文档导入 → 检索 → 生成回答 |
| Memory使用 | 任务执行 → 记忆存储 → 后续任务检索 |
| 认证流程 | 注册 → 登录 → 访问受保护API |

### 11.3 前端测试

- 组件渲染测试（AgentMonitor, Chat, Settings）
- Store状态更新测试（authStore）
- API调用测试（认证流程）

---

## 12. 验收标准

### 12.1 功能验收

- [ ] 6个新工具可独立测试和执行
- [ ] CodeExecuteTool能安全执行Python代码并阻止危险操作
- [ ] FileIOTool限制在项目目录内
- [ ] 3个新Agent角色可创建和执行任务
- [ ] JWT认证可注册/登录/保护API
- [ ] Memory系统支持三层记忆的CRUD
- [ ] RAG系统可导入文档并检索
- [ ] Reflection引擎生成有价值的反思报告
- [ ] 前端AgentMonitor实时显示Agent状态
- [ ] 前端Chat支持多Agent对话
- [ ] 前端Settings可配置系统参数

### 12.2 质量验收

- [ ] 后端测试覆盖率 > 70%
- [ ] 所有单元测试通过
- [ ] 集成测试覆盖主要场景
- [ ] black + isort格式化通过
- [ ] mypy类型检查通过
- [ ] 前端ESLint无错误

### 12.3 演示场景

**场景1**：编程任务
```
用户: "写一个Python函数计算斐波那契数列"
系统:
1. Planner拆解任务
2. CoderAgent编写代码（FileWrite）
3. CoderAgent测试代码（CodeExecute）
4. 返回代码 + 测试结果
5. Reflection报告总结
```

**场景2**：知识库问答
```
用户上传Python文档 → 系统导入知识库
用户提问: "Python async/await最佳实践"
系统:
1. RAG检索知识库
2. ResearcherAgent分析
3. 返回详细回答（带引用来源）
```

**场景3**：多Agent协作
```
用户: "研究Python性能优化并写一篇博客"
系统:
1. Planner拆解: [搜索资料, 分析资料, 撰写博客, 审查]
2. ResearcherAgent搜索（WebSearch + RAG）
3. WriterAgent撰写（Summarize + FileWrite）
4. ReviewerAgent审查
5. 返回最终博客
```

---

## 13. 风险缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| CodeExecuteTool安全性 | 高 | 高 | 多层安全（AST扫描+子进程隔离+超时） |
| ChromaDB性能 | 中 | 中 | 批量插入、索引优化 |
| LLM Embedding成本 | 中 | 低 | 本地模型fallback、缓存 |
| 前端认证复杂度 | 中 | 中 | 使用成熟库（axios拦截器） |
| JWT密钥泄露 | 低 | 高 | 环境变量配置、定期轮换 |

---

## 附录

### A. 文件清单

**Day 1**:
- `tools/code_execute.py`
- `tools/file_io.py`
- `tools/summarize.py`
- `tools/agent_message.py`

**Day 2**:
- `tools/memory_search.py`
- `tools/web_browser.py`
- `tests/unit/test_code_execute.py`
- `tests/unit/test_file_io.py`
- `tests/unit/test_summarize.py`
- `tests/unit/test_agent_message.py`

**Day 3**:
- `api/routes/auth.py`
- `database/models.py`（更新：UserORM）
- `agents/coder_agent.py`
- `agents/writer_agent.py`
- `agents/reviewer_agent.py`
- `agents/factory.py`（更新）

**Day 4**:
- `core/memory_manager.py`
- `database/models.py`（更新：MemoryORM）

**Day 5**:
- `core/rag_system.py`
- `tools/memory_search.py`（更新：接入RAG）

**Day 6**:
- `core/reflection_engine.py`
- `core/orchestrator.py`（更新：集成Reflection）

**Day 7**:
- `frontend/src/pages/AgentMonitor.tsx`
- `frontend/src/pages/MultiAgentChat.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/stores/authStore.ts`
- `frontend/src/api/client.ts`（更新：认证）

**Day 8**:
- `api/middleware/rate_limit.py`
- `tests/integration/test_week3.py`

### B. 技术依赖

**新增依赖**：
```
# 后端
PyPDF2==3.0.1              # PDF解析
beautifulsoup4==4.12.2     # HTML解析
duckduckgo-search==3.9.6   # Web搜索

# 前端（已在Week 2安装）
react-router-dom
zustand
axios
lucide-react
```

---

> **设计文档结束**
> 
> 下一步：创建详细实施计划或开始编码实现
