# Week 1 详细任务清单（文件级）

> **目标**: 基础设施 + 核心引擎  
> **周期**: Week 1（建议 5-7 天完成）  
> **依赖**: 无（第一周，基础层）  

---

## 环境准备（前置步骤）

### Anaconda 虚拟环境配置

```bash
# 1. 创建虚拟环境（Python 3.11）
conda create -n agentforge python=3.11 -y

# 2. 激活虚拟环境（!!! 重要：所有操作都在此环境下执行)
conda activate agentforge

# 3. 验证环境
python --version  # 应显示 Python 3.11.x
which python      # 应显示 anaconda3/envs/agentforge/bin/python

# 4. 安装基础工具
pip install --upgrade pip setuptools wheel

# 5. 创建项目目录
mkdir -p ~/Projects/AgentForge
cd ~/Projects/AgentForge

# 6. 目录结构
mkdir -p backend/agent_forge/{core,agents,mcp,tools,models,database,config,api/middleware,utils}
mkdir -p backend/tests/{unit,integration,fixtures}
mkdir -p docs
mkdir -p scripts
```

### 依赖文件清单

创建 `backend/requirements.txt`:

```
# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# 数据验证
pydantic==2.5.2
pydantic-settings==2.1.0
email-validator==2.1.0

# 数据库
sqlalchemy==2.0.23
aiosqlite==0.19.0
asyncpg==0.29.0
alembic==1.12.1

# 向量数据库
chromadb==0.4.18

# LLM 客户端
openai==1.3.6
httpx==0.25.2

# 工具
duckduckgo-search==3.9.6
beautifulsoup4==4.12.2
PyPDF2==3.0.1

# 安全
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
cryptography==41.0.7

# 缓存/消息队列
redis==5.0.1

# 监控
psutil==5.9.6

# 配置
python-dotenv==1.0.0
PyYAML==6.0.1

# 日志
structlog==23.2.0

# 测试
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
pytest-mock==3.12.0
factory-boy==3.3.0
faker==20.1.0

# 代码质量
black==23.11.0
isort==5.12.0
flake8==6.1.0
mypy==1.7.1

# 类型提示
types-PyYAML==6.0.12.12
```

创建 `backend/requirements-dev.txt`:

```
-r requirements.txt

# 开发工具
jupyter==1.0.0
ipython==8.17.2

# 调试
pdbpp==0.10.3
```

安装依赖:
```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 任务分解

### 批次 1A: 最基础层（无依赖）

#### 任务 1: 配置管理
**文件**: `backend/agent_forge/config/settings.py`
```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "AgentForge"
    ENVIRONMENT: str = "development"
    
    # 数据库
    DB_TYPE: str = "sqlite"
    DATABASE_URL: str = "sqlite:///data/agentforge.db"
    
    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 7
    
    # 加密
    ENCRYPTION_KEY: str
    ENCRYPTION_SALT: str = "agentforge-salt"
    
    # LLM
    KIMI_API_KEY: Optional[str] = None
    KIMI_BASE_URL: str = "https://api.moonshot.cn"
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

**依赖**: 无（最底层）  
**被依赖**: 所有其他模块  
**验收**: `python -c "from config.settings import settings; print(settings.APP_NAME)"` 正常输出

---

#### 任务 2: 数据模型
**文件**: `backend/agent_forge/models/schemas.py`
```python
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentRole(str, Enum):
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    WRITER = "writer"
    REVIEWER = "reviewer"
    EXECUTOR = "executor"

class StepType(str, Enum):
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    FINAL = "final"
    ERROR = "error"

# 核心模型（先定义基础模型，后续逐步添加）
class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentStep(BaseModel):
    task_id: str
    agent_id: str
    step_number: int
    step_type: StepType
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

**依赖**: 无（纯 Pydantic）  
**被依赖**: core/, agents/, api/  
**验收**: `pytest tests/unit/test_schemas.py` 通过

---

#### 任务 3: 错误处理
**文件**: `backend/agent_forge/core/error_handler.py`
```python
from enum import Enum
from typing import Dict, Any, Optional

class ErrorCode(str, Enum):
    UNKNOWN_ERROR = "10000"
    INTERNAL_ERROR = "10001"
    INVALID_PARAMETER = "20000"
    UNAUTHORIZED = "30000"
    TASK_NOT_FOUND = "40000"
    LLM_CALL_FAILED = "40002"
    RATE_LIMIT_EXCEEDED = "50000"

class AppException(Exception):
    def __init__(self, code: ErrorCode, message: str, 
                 details: Optional[Dict] = None, status_code: int = 500):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)
```

**依赖**: 无  
**被依赖**: 所有模块  
**验收**: 可抛出和捕获 AppException

---

#### 任务 4: 取消控制
**文件**: `backend/agent_forge/core/cancellation.py`
```python
class CancellationToken:
    def __init__(self):
        self._cancelled = False
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def cancel(self):
        self._cancelled = True
    
    def check_cancellation(self):
        if self._cancelled:
            raise CancellationError("任务已取消")

class CancellationError(Exception):
    pass
```

**依赖**: 无  
**被依赖**: core/react_loop.py, core/orchestrator.py  
**验收**: `CancellationToken` 可正常取消

---

### 批次 1B: 基础层（依赖 1A）

#### 任务 5: 输出验证
**文件**: `backend/agent_forge/core/output_validator.py`
```python
from typing import Type, Dict, Any
from pydantic import BaseModel, ValidationError as PydanticValidationError
import json

class ValidationError(Exception):
    pass

class OutputValidator:
    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
    
    def validate(self, data: Dict[str, Any]) -> BaseModel:
        try:
            return self.model_class(**data)
        except PydanticValidationError as e:
            raise ValidationError(f"Schema 验证失败: {e}")
    
    def validate_json(self, json_str: str) -> BaseModel:
        try:
            data = json.loads(json_str)
            return self.validate(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON 解析失败: {e}")
```

**依赖**: Pydantic  
**被依赖**: core/react_loop.py  
**验收**: 可验证和捕获验证错误

---

#### 任务 6: 数据库连接
**文件**: `backend/agent_forge/database/connection.py`
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config.settings import settings

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development"
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
        await session.commit()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**依赖**: config/settings.py, SQLAlchemy  
**被依赖**: api/, core/  
**验收**: `init_db()` 可创建表

---

#### 任务 7: 日志系统
**文件**: `backend/agent_forge/utils/logging.py`
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module
        }
        return json.dumps(log_data)

def setup_logging():
    logger = logging.getLogger()
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

**依赖**: 无  
**被依赖**: 所有模块  
**验收**: 日志输出 JSON 格式

---

### 批次 2A: 核心能力层（依赖 1A+1B）

#### 任务 8: LLM 客户端 + 路由
**文件**: `backend/agent_forge/core/llm_client.py`
```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass
import httpx

@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: int

@dataclass
class StreamChunk:
    content: str
    is_finished: bool = False

class BaseLLMProvider(ABC):
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    @abstractmethod
    async def chat(self, messages, model, **kwargs) -> LLMResponse:
        pass

class LLMRouter:
    def __init__(self):
        self.providers = {}
        self.fallback_chain = []
    
    def register_provider(self, name: str, provider: BaseLLMProvider):
        self.providers[name] = provider
    
    async def route(self, messages, complexity="medium", **kwargs):
        # 实现路由逻辑
        pass
```

**依赖**: httpx, config/settings.py  
**被依赖**: core/react_loop.py, core/planner.py  
**验收**: 可注册和调用 Provider

---

#### 任务 9: ReAct 引擎
**文件**: `backend/agent_forge/core/react_loop.py`
```python
import json
from typing import AsyncGenerator, List, Dict, Optional
from pydantic import BaseModel, Field
from models.schemas import AgentStep, StepType
from core.llm_client import LLMRouter
from core.cancellation import CancellationToken
from core.output_validator import OutputValidator

class ReActOutput(BaseModel):
    thought: str
    action: Optional[Dict] = None
    is_final: bool = False
    final_answer: Optional[str] = None

class ReActLoop:
    def __init__(self, llm_router, tools, max_steps=10):
        self.llm_router = llm_router
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.validator = OutputValidator(ReActOutput)
    
    async def run(self, task, context=None, cancellation_token=None):
        # 实现 ReAct 循环
        pass
    
    async def _get_llm_response_with_retry(self, messages, max_retries=3):
        # 实现重试逻辑
        pass
```

**依赖**: models/schemas.py, core/llm_client.py, core/cancellation.py, core/output_validator.py  
**被依赖**: agents/base.py  
**验收**: 可执行 ReAct 循环，JSON 解析成功率 > 95%

---

#### 任务 10: 工具基类
**文件**: `backend/agent_forge/tools/base.py`
```python
from abc import ABC, abstractmethod
from typing import Dict, Any
from pydantic import BaseModel, Field

class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]
    required: list[str] = Field(default_factory=list)

class BaseTool(ABC):
    name: str = ""
    description: str = ""
    
    def __init__(self):
        self.schema = self._build_schema()
    
    @abstractmethod
    def _build_schema(self) -> ToolSchema:
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> str:
        pass
    
    def get_schema(self):
        return self.schema.model_dump()
```

**依赖**: Pydantic  
**被依赖**: tools/*.py, mcp/tool_registry.py  
**验收**: 可继承实现具体工具

---

#### 任务 11: MCP 注册中心
**文件**: `backend/agent_forge/mcp/tool_registry.py`
```python
from typing import Dict, List
from tools.base import BaseTool

class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._categories = {}
    
    def register(self, tool: BaseTool, category="general"):
        self._tools[tool.name] = tool
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)
    
    def get(self, tool_name: str):
        return self._tools.get(tool_name)
    
    def list_tools(self, category=None):
        # 实现列表逻辑
        pass
```

**依赖**: tools/base.py  
**被依赖**: core/react_loop.py  
**验收**: 可注册和获取工具

---

#### 任务 12: Agent 基类
**文件**: `backend/agent_forge/agents/base.py`
```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List
from models.schemas import AgentStep, AgentRole
from core.llm_client import LLMRouter
from core.react_loop import ReActLoop

class BaseAgent(ABC):
    def __init__(self, role, llm_router, tools=None, max_steps=10):
        self.role = role
        self.llm_router = llm_router
        self.tools = tools or []
        self.max_steps = max_steps
        self.react_loop = ReActLoop(
            llm_router=llm_router,
            tools=self.get_tools(),
            max_steps=max_steps
        )
    
    @abstractmethod
    def _get_name(self) -> str:
        pass
    
    def get_tools(self):
        return self.tools
    
    async def run(self, task, context=None):
        async for step in self.react_loop.run(task, context):
            yield step
```

**依赖**: models/schemas.py, core/llm_client.py, core/react_loop.py  
**被依赖**: agents/*_agent.py  
**验收**: 可继承实现具体 Agent

---

## 执行顺序

```
Day 1: 任务 1-4（最基础层，无依赖）
       ├── 创建虚拟环境
       ├── 安装依赖
       ├── config/settings.py
       ├── models/schemas.py
       ├── core/error_handler.py
       └── core/cancellation.py

Day 2: 任务 5-7（基础层）
       ├── core/output_validator.py
       ├── database/connection.py
       └── utils/logging.py

Day 3: 任务 8-9（核心能力）
       ├── core/llm_client.py
       └── core/react_loop.py

Day 4: 任务 10-12（工具 + Agent）
       ├── tools/base.py
       ├── mcp/tool_registry.py
       └── agents/base.py

Day 5: 测试 + 修复
       ├── 编写单元测试
       ├── 集成测试
       └── Bug 修复
```

---

## 验收检查清单

### 环境检查
- [ ] Anaconda 虚拟环境 `agentforge` 已创建
- [ ] Python 版本 3.11+
- [ ] 所有依赖已安装
- [ ] `pytest` 可运行

### 文件检查
- [ ] `config/settings.py` - 可加载配置
- [ ] `models/schemas.py` - 所有模型可实例化
- [ ] `core/error_handler.py` - 异常可捕获
- [ ] `core/cancellation.py` - 取消令牌工作
- [ ] `core/output_validator.py` - 验证逻辑正确
- [ ] `database/connection.py` - 可连接数据库
- [ ] `utils/logging.py` - JSON 日志输出
- [ ] `core/llm_client.py` - 可注册 Provider
- [ ] `core/react_loop.py` - ReAct 循环可执行
- [ ] `tools/base.py` - 可继承实现工具
- [ ] `mcp/tool_registry.py` - 工具可注册
- [ ] `agents/base.py` - 可继承实现 Agent

### 测试检查
- [ ] 后端测试覆盖率 > 60%
- [ ] 所有单元测试通过
- [ ] 无类型错误（mypy）
- [ ] 代码格式正确（black + isort）

---

**Week 1 详细任务清单结束**

> 下一步: 开始按此清单编码实现
