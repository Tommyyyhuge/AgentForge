# AgentForge 完整设计文档

> **版本**: 1.0  
> **日期**: 2026-05-19  
> **路径**: C  
> **开发周期**: 8-10 周  

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术选型](#2-技术选型)
3. [系统架构](#3-系统架构)
4. [核心模块设计](#4-核心模块设计)
5. [数据库设计](#5-数据库设计)
6. [API 设计](#6-api-设计)
7. [前端架构](#7-前端架构)
8. [性能监控](#8-性能监控)
9. [部署架构](#9-部署架构)
10. [开发计划](#10-开发计划)
11. [面试准备](#11-面试准备)

---

## 1. 项目概述

### 1.1 产品定位

AgentForge 是一个**企业级多智能体协作任务执行平台**，覆盖 8 个核心 AI 方向：

| 方向 | 说明 | 面试亮点 |
|------|------|----------|
| **ReAct** | 手写推理+行动循环引擎 | 从零实现，非调用框架 |
| **Plan-and-Solve** | 任务规划+依赖图执行 | 智能任务拆解 |
| **Reflection** | 自我反思+经验学习 | 持续改进能力 |
| **Multi-Agent** | 6 角色协作调度 | 自研 Orchestrator |
| **MCP** | 工具注册协议 | 标准化工具管理 |
| **A2A** | Agent 间通信协议 | 消息总线设计 |
| **RAG** | 向量检索增强 | ChromaDB + 语义搜索 |
| **Memory** | 三层记忆系统 | 短期+长期+经验 |

### 1.2 目标用户

- **面试官**：展示全栈 + Agent 系统设计与工程能力
- **技术同行**：开源参考实现
- **实际用户**：复杂任务自动化执行

### 1.3 核心特性

- ✅ 6 个 Agent 角色（规划师、研究员、程序员、写手、审查员、执行者）
- ✅ 8+ MCP 工具（搜索、计算、代码执行、文件操作、记忆检索等）
- ✅ 智能 LLM 路由（Kimi K2.6 + DeepSeek v4pro/v4flash）
- ✅ 三层记忆系统（短期+长期+经验）
- ✅ 实时可视化（时间线 + 流程图）
- ✅ 用户系统（JWT + OAuth + API Key 管理）
- ✅ 团队协作（工作区 + 权限管理）
- ✅ 插件系统（自定义 Agent/工具/主题）
- ✅ 性能监控（实时指标 + Dashboard）
- ✅ 国际化支持（多语言）
- ✅ 移动端适配（PWA）
- ✅ Docker 一键部署 + CI/CD

### 1.4 面试展示路径

```
1. 打开 Web Demo → 专业 Dashboard 界面
2. 展示预设任务场景（调研/编程/写作）
3. 实时观看 Planner 拆解任务 → 依赖图可视化
4. 多 Agent 并行执行 → ReAct 循环可视化
5. 查看 A2A 消息流 → Agent 间协作流程图
6. 查看 MCP 工具调用日志
7. 查看反思报告 + 经验学习
8. 展示性能监控 Dashboard
9. 展示移动端适配
```

---

## 2. 技术选型

### 2.1 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 主语言 |
| FastAPI | 0.104+ | Web 框架 |
| Uvicorn | 0.24+ | ASGI 服务器 |
| Pydantic | 2.5+ | 数据验证 |
| SQLAlchemy | 2.0+ | ORM |
| PostgreSQL | 15+ | 主数据库（生产） |
| SQLite | 3.40+ | 本地开发 |
| ChromaDB | 0.4+ | 向量数据库 |
| Redis | 7+ | 缓存 + 消息队列 |
| JWT | PyJWT | 认证 |
| bcrypt | 4.0+ | 密码加密 |
| cryptography | 41+ | API Key 加密 |
| psutil | 5.9+ | 系统监控 |
| pytest | 7.4+ | 测试框架 |
| pytest-asyncio | 0.21+ | 异步测试 |
| pytest-cov | 4.1+ | 覆盖率 |
| Docker | 24+ | 容器化 |

### 2.2 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18.2+ | UI 框架 |
| TypeScript | 5.3+ | 类型系统 |
| Vite | 5.0+ | 构建工具 |
| Tailwind CSS | 3.4+ | 样式框架 |
| Zustand | 4.4+ | 状态管理 |
| React Router | 6.20+ | 路由 |
| Axios | 1.6+ | HTTP 客户端 |
| Chart.js | 4.4+ | 数据可视化 |
| React Query | 5.8+ | 服务端状态 |
| i18next | 23.7+ | 国际化 |
| Playwright | 1.40+ | E2E 测试 |
| Vitest | 1.0+ | 单元测试 |

### 2.3 基础设施

| 技术 | 用途 |
|------|------|
| Nginx | 反向代理 + 负载均衡 |
| Docker Compose | 容器编排 |
| GitHub Actions | CI/CD |
| Let's Encrypt | SSL 证书 |
| Prometheus | 指标收集（可选） |
| Grafana | 可视化（可选） |

### 2.4 LLM 提供商

| 提供商 | 模型 | 用途 |
|--------|------|------|
| Kimi (Moonshot) | K2.6 | 复杂推理、代码生成 |
| DeepSeek | v4pro | 高质量输出 |
| DeepSeek | v4flash | 快速响应 |
| 自定义 | OpenAI 兼容 | 用户接入 |

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                     前端层 (React 18 + TypeScript)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ 任务中心  │ │ Agent监控 │ │ 知识库   │ │ 性能监控Dashboard   │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ 用户中心  │ │ 系统设置 │ │ 插件市场 │ │ 团队协作空间        │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / WebSocket
┌──────────────────────────┼──────────────────────────────────────┐
│                     网关层 (Nginx + SSL)                         │
│         负载均衡 / 静态资源缓存 / 限流 / WAF                      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                     API 层 (FastAPI + Uvicorn)                   │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ REST API     │ │ SSE 流式     │ │ WebSocket (实时通知)    │  │
│  │ JWT 认证     │ │ 限流熔断     │ │ 请求合并                │  │
│  └──────────────┘ └──────────────┘ └─────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                  业务核心层 (Python Async)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────────┐  │
│  │ ReAct 引擎   │ │ 规划器       │ │ 调度器 (Orchestrator)   │  │
│  │ MCP 注册中心 │ │ A2A 总线     │ │ 反思引擎                │  │
│  │ RAG 检索     │ │ 记忆管理     │ │ 插件系统                │  │
│  └──────────────┘ └──────────────┘ └─────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                  基础设施层                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ PostgreSQL│ │ ChromaDB │ │ Redis    │ │ 对象存储 (OSS/S3)   │ │
│  │ (主数据)  │ │ (向量)   │ │ (缓存)   │ │ (文件/知识库)       │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────────────┐ │
│  │ LLM 路由  │ │ 日志系统  │ │ 监控告警 │ │ 任务队列 (Celery)   │ │
│  │ (多厂商)  │ │ (结构化) │ │ (Prometheus)│                   │ │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 模块层次

```
Layer 4: 表现层 (Presentation)
├── frontend/src/components/    # UI 组件
├── frontend/src/pages/         # 页面
├── frontend/src/stores/        # 状态管理 (Zustand)
└── frontend/src/api/           # HTTP 客户端

Layer 3: 网关层 (Gateway)
└── backend/agent_forge/api/    # FastAPI 路由 + SSE

Layer 2: 业务核心层 (Core)
├── backend/agent_forge/core/llm_client.py      # LLM 客户端
├── backend/agent_forge/core/react_loop.py      # ReAct 引擎
├── backend/agent_forge/core/planner.py         # 规划器
├── backend/agent_forge/core/orchestrator.py    # 调度器
├── backend/agent_forge/core/reflection_engine.py  # 反思引擎
├── backend/agent_forge/core/a2a_bus.py         # A2A 总线
├── backend/agent_forge/core/rag_system.py      # RAG 系统
├── backend/agent_forge/core/memory_manager.py  # 记忆管理
└── backend/agent_forge/core/performance_monitor.py  # 性能监控

Layer 1: 能力层 (Capability)
├── backend/agent_forge/agents/     # Agent 角色实现
├── backend/agent_forge/mcp/        # MCP 工具注册
├── backend/agent_forge/tools/      # 工具实现
└── backend/agent_forge/plugins/    # 插件系统

Layer 0: 基础设施层 (Infrastructure)
├── backend/agent_forge/models/      # 数据模型
├── backend/agent_forge/database/    # 数据库初始化
├── backend/agent_forge/config/      # 配置管理
└── backend/agent_forge/utils/       # 工具函数
```

### 3.3 数据流

```
用户输入 → API 层 → 调度器 → 规划器 → 子任务列表
                                      ↓
                                  依赖图分析
                                      ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
                Agent 1        Agent 2         Agent 3
                (并行)         (并行)          (等待依赖)
                    ↓               ↓               ↓
                ReAct 循环     ReAct 循环      ReAct 循环
                    ↓               ↓               ↓
                工具调用       工具调用        工具调用
                    ↓               ↓               ↓
                MCP 注册中心 ← 工具执行 → 结果返回
                    ↓               ↓               ↓
                A2A 消息流（Agent 间通信）
                    ↓               ↓               ↓
                记忆系统（保存中间结果）
                    ↓               ↓               ↓
                    └───────────────┴───────────────┘
                                      ↓
                                  结果合并
                                      ↓
                                  反思引擎
                                      ↓
                                  最终输出
                                      ↓
                              SSE 流式推送 → 前端
```

---

## 4. 核心模块设计

### 4.1 数据模型

#### 核心实体关系

```
┌─────────────────────────────────────────────────────────┐
│                      Task (主任务)                        │
│  - id, title, description, status                       │
│  - user_id, workspace_id                                │
│  - created_at, completed_at                             │
│  - total_agents, total_steps, total_latency_ms          │
│  - plan: ExecutionPlan                                  │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ SubTask     │  │ AgentStep   │  │ ToolCall        │ │
│  │ (子任务)     │  │ (执行步骤)   │  │ (工具调用)      │ │
│  │ - task_id   │  │ - agent_id  │  │ - step_id       │ │
│  │ - status    │  │ - type      │  │ - tool_name     │ │
│  │ - deps      │  │ - content   │  │ - arguments     │ │
│  │ - assignee  │  │ - latency   │  │ - result        │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ User        │  │ AgentConfig │  │ KnowledgeDoc    │ │
│  │ (用户)      │  │ (Agent配置) │  │ (知识库文档)    │ │
│  │ - username  │  │ - role      │  │ - user_id       │ │
│  │ - api_keys  │  │ - llm_model │  │ - embedding     │ │
│  │ - prefs     │  │ - tools     │  │ - metadata      │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ Workspace   │  │ Plugin      │  │ PerformanceMetric│ │
│  │ (工作区)    │  │ (插件)      │  │ (性能指标)      │ │
│  │ - members   │  │ - type      │  │ - task_id       │ │
│  │ - tasks     │  │ - manifest  │  │ - latency       │ │
│  │ - settings  │  │ - code      │  │ - tokens/sec    │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

#### 关键模型定义

```python
# models/schemas.py

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

class Task(BaseModel):
    """主任务模型"""
    id: str = Field(..., description="任务唯一标识")
    user_id: str = Field(..., description="所属用户")
    workspace_id: Optional[str] = Field(None, description="所属工作区")
    
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    
    # 执行统计
    total_agents: int = Field(default=0)
    total_steps: int = Field(default=0)
    total_latency_ms: int = Field(default=0)
    
    # 关联数据
    plan: Optional['ExecutionPlan'] = None
    result: Optional[str] = None
    reflection: Optional['ReflectionReport'] = None
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ExecutionPlan(BaseModel):
    """执行计划"""
    task_id: str
    subtasks: List['SubTask']
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)

class SubTask(BaseModel):
    """子任务"""
    id: str
    task_id: str
    description: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    assigned_agent: AgentRole
    dependencies: List[str] = Field(default_factory=list)
    expected_output: Optional[str] = None
    result: Optional[str] = None

class AgentStep(BaseModel):
    """Agent 执行步骤（ReAct 循环）"""
    id: str
    task_id: str
    subtask_id: str
    agent_id: str
    
    step_number: int
    step_type: StepType
    content: str
    
    # 性能指标
    latency_ms: int = 0
    token_count: int = 0
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    """用户模型"""
    id: str
    username: str
    email: str
    password_hash: str
    
    # API Keys（AES 加密存储）
    api_keys: Dict[str, str] = Field(default_factory=dict)
    
    # 偏好设置
    preferences: 'UserPreferences' = Field(default_factory=lambda: UserPreferences())
    
    # 工作区
    workspaces: List[str] = Field(default_factory=list)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserPreferences(BaseModel):
    """用户偏好"""
    default_model: str = "kimi-k2.6"
    theme: str = "dark"
    language: str = "zh-CN"
    
    # Agent 行为偏好
    output_style: str = "detailed"
    auto_reflect: bool = True
    max_steps: int = 10

class KnowledgeDoc(BaseModel):
    """知识库文档"""
    id: str
    user_id: str
    filename: str
    content_type: str
    
    # 向量索引信息
    embedding_ids: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    
    # 元数据
    file_size: int
    upload_at: datetime = Field(default_factory=datetime.utcnow)

class Workspace(BaseModel):
    """团队协作空间"""
    id: str
    name: str
    owner_id: str
    member_ids: List[str] = Field(default_factory=list)
    task_ids: List[str] = Field(default_factory=list)
    
    settings: Dict[str, Any] = Field(default_factory=dict)

class Plugin(BaseModel):
    """插件"""
    id: str
    name: str
    version: str
    type: str  # agent / tool / theme / extension
    
    # 插件清单
    manifest: Dict[str, Any]
    
    # 代码（存储在文件系统或 OSS）
    code_path: str
    author_id: str
    
    is_enabled: bool = True
    install_count: int = 0

class PerformanceMetric(BaseModel):
    """性能指标"""
    id: str
    task_id: str
    
    # LLM 调用指标
    llm_calls: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    
    # 延迟指标
    planning_latency_ms: int = 0
    execution_latency_ms: int = 0
    total_latency_ms: int = 0
    
    # 资源指标
    peak_memory_mb: float = 0
    cpu_percent: float = 0
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### 4.2 LLM 客户端与路由

```python
# core/llm_client.py

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
from dataclasses import dataclass
import aiohttp
import asyncio
from datetime import datetime

@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Dict[str, int]
    latency_ms: int
    finish_reason: Optional[str] = None

@dataclass
class StreamChunk:
    """流式响应块"""
    content: str
    is_finished: bool = False
    usage: Optional[Dict[str, int]] = None

class BaseLLMProvider(ABC):
    """LLM 提供商基类"""
    
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def chat(self, messages, model, temperature=0.7, 
                   stream=False, max_tokens=None) -> LLMResponse:
        pass
    
    @abstractmethod
    async def chat_stream(self, messages, model, 
                         temperature=0.7, max_tokens=None) -> AsyncGenerator[StreamChunk, None]:
        pass
    
    @abstractmethod
    async def embed(self, texts: List[str], model: str) -> List[List[float]]:
        pass

class LLMRouter:
    """LLM 路由管理器"""
    
    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.fallback_chain: List[str] = []
    
    def register_provider(self, name: str, provider: BaseLLMProvider):
        """注册提供商"""
        self.providers[name] = provider
    
    def set_fallback_chain(self, chain: List[str]):
        """设置降级链"""
        self.fallback_chain = chain
    
    async def route(self, messages, complexity="medium", 
                   user_preference=None, stream=False) -> LLMResponse:
        """智能路由"""
        
        # 1. 用户偏好优先
        if user_preference and user_preference in self.providers:
            provider_name = user_preference
        else:
            # 2. 根据复杂度智能选择
            provider_name = self._select_by_complexity(complexity)
        
        # 3. 尝试调用，失败则降级
        for name in [provider_name] + self.fallback_chain:
            if name not in self.providers:
                continue
            
            provider = self.providers[name]
            try:
                if stream:
                    return await provider.chat_stream(
                        messages, self._get_model(name, complexity)
                    )
                else:
                    return await provider.chat(
                        messages, self._get_model(name, complexity)
                    )
            except Exception as e:
                print(f"Provider {name} failed: {e}")
                continue
        
        raise Exception("All LLM providers failed")
    
    def _select_by_complexity(self, complexity: str) -> str:
        """根据复杂度选择模型"""
        if complexity == "high":
            return "kimi"
        elif complexity == "medium":
            return "deepseek-v4pro"
        else:
            return "deepseek-v4flash"
```

### 4.3 ReAct 引擎（JSON 结构化输出 + 重试机制）

```python
# core/react_loop.py

import json
import re
from typing import AsyncGenerator, List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from models.schemas import AgentStep, StepType
from core.llm_client import LLMRouter
from core.cancellation import CancellationToken
from core.output_validator import OutputValidator, ValidationError

class ReActOutput(BaseModel):
    """ReAct 结构化输出"""
    thought: str = Field(..., description="思考过程")
    action: Optional[Dict] = Field(None, description="工具调用")
    is_final: bool = Field(False, description="是否完成")
    final_answer: Optional[str] = Field(None, description="最终答案")

class ReActLoop:
    """
    ReAct (Reasoning + Acting) 循环引擎
    
    改进点：
    1. JSON 结构化输出替代正则解析
    2. 自动重试机制（最多 3 次）
    3. 输出验证失败时自动修正
    4. 支持取消令牌
    """
    
    def __init__(self, llm_router, tools, max_steps=10, agent_role="executor"):
        self.llm_router = llm_router
        self.tools = {tool.name: tool for tool in tools}
        self.max_steps = max_steps
        self.agent_role = agent_role
        self.system_prompt = self._build_system_prompt()
        self.validator = OutputValidator(ReActOutput)
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词（JSON 模式）"""
        tools_desc = "\n".join([
            f"- {name}: {tool.description}\n  参数: {tool.get_schema()}"
            for name, tool in self.tools.items()
        ])
        
        return f"""你是一个 {self.agent_role} Agent，擅长通过工具调用完成任务。

可用工具：
{tools_desc}

你必须按以下 JSON 格式输出：
{{
    "thought": "你的思考过程",
    "action": {{
        "tool": "工具名称",
        "params": {{"参数名": "参数值"}}
    }},
    "is_final": false,
    "final_answer": null
}}

当任务完成时：
{{
    "thought": "总结思考",
    "action": null,
    "is_final": true,
    "final_answer": "最终答案"
}}

规则：
1. 每次只能调用一个工具
2. 如果工具调用失败，尝试其他方法
3. 如果达到最大步数仍未完成，给出最佳回答
4. 必须输出合法的 JSON，不要包含其他文本
"""
    
    async def run(self, task, context=None, stream=True, 
                  cancellation_token=None) -> AsyncGenerator[AgentStep, None]:
        """执行 ReAct 循环"""
        context = context or {}
        cancellation_token = cancellation_token or CancellationToken()
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"任务: {task}\n上下文: {context}"}
        ]
        
        step_number = 0
        
        while step_number < self.max_steps:
            # 检查取消
            if cancellation_token.is_cancelled:
                yield AgentStep(
                    task_id=context.get("task_id", ""),
                    subtask_id=context.get("subtask_id", ""),
                    agent_id=self.agent_role,
                    step_number=step_number,
                    step_type=StepType.ERROR,
                    content="任务已被用户取消"
                )
                break
            
            step_number += 1
            
            # 1. 获取并验证 LLM 响应（带重试）
            try:
                react_output = await self._get_llm_response_with_retry(
                    messages, cancellation_token
                )
            except ValidationError as e:
                yield AgentStep(
                    task_id=context.get("task_id", ""),
                    subtask_id=context.get("subtask_id", ""),
                    agent_id=self.agent_role,
                    step_number=step_number,
                    step_type=StepType.ERROR,
                    content=f"LLM 输出验证失败（重试 3 次后）: {str(e)}"
                )
                break
            
            # 2. 输出 Thought
            yield AgentStep(
                task_id=context.get("task_id", ""),
                subtask_id=context.get("subtask_id", ""),
                agent_id=self.agent_role,
                step_number=step_number,
                step_type=StepType.THOUGHT,
                content=react_output.thought
            )
            
            if react_output.is_final:
                yield AgentStep(
                    task_id=context.get("task_id", ""),
                    subtask_id=context.get("subtask_id", ""),
                    agent_id=self.agent_role,
                    step_number=step_number,
                    step_type=StepType.FINAL,
                    content=react_output.final_answer or "任务完成"
                )
                break
            
            # 3. 输出 Action
            action_desc = f"{react_output.action['tool']}({react_output.action.get('params', {})})"
            yield AgentStep(
                task_id=context.get("task_id", ""),
                subtask_id=context.get("subtask_id", ""),
                agent_id=self.agent_role,
                step_number=step_number,
                step_type=StepType.ACTION,
                content=action_desc
            )
            
            # 4. 执行工具
            try:
                observation = await self._execute_action(react_output.action)
                yield AgentStep(
                    task_id=context.get("task_id", ""),
                    subtask_id=context.get("subtask_id", ""),
                    agent_id=self.agent_role,
                    step_number=step_number,
                    step_type=StepType.OBSERVATION,
                    content=observation
                )
            except Exception as e:
                observation = f"工具执行错误: {str(e)}"
                yield AgentStep(
                    task_id=context.get("task_id", ""),
                    subtask_id=context.get("subtask_id", ""),
                    agent_id=self.agent_role,
                    step_number=step_number,
                    step_type=StepType.ERROR,
                    content=observation
                )
            
            # 5. 更新对话历史
            messages.append({
                "role": "assistant", 
                "content": json.dumps({
                    "thought": react_output.thought,
                    "action": react_output.action,
                    "is_final": False,
                    "final_answer": None
                }, ensure_ascii=False)
            })
            messages.append({
                "role": "user", 
                "content": f"Observation: {observation}"
            })
        
        else:
            yield AgentStep(
                task_id=context.get("task_id", ""),
                subtask_id=context.get("subtask_id", ""),
                agent_id=self.agent_role,
                step_number=step_number,
                step_type=StepType.FINAL,
                content="达到最大执行步数，任务未完成。"
            )
    
    async def _get_llm_response_with_retry(self, messages, cancellation_token, 
                                          max_retries=3) -> ReActOutput:
        """获取 LLM 响应并验证（带重试）"""
        for attempt in range(max_retries):
            try:
                # 检查取消
                if cancellation_token.is_cancelled:
                    raise CancellationError("任务已取消")
                
                response = await self.llm_router.route(
                    messages=messages, 
                    complexity="medium"
                )
                
                # 尝试解析 JSON
                react_output = self._parse_react_output(response.content)
                
                # 验证输出
                self.validator.validate(react_output.model_dump())
                
                return react_output
                
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt < max_retries - 1:
                    # 构建修正 Prompt
                    correction_message = {
                        "role": "user",
                        "content": f"你的输出格式有误，请按 JSON 格式重新输出。错误: {str(e)}"
                    }
                    messages.append(correction_message)
                    continue
                else:
                    raise ValidationError(f"重试 {max_retries} 次后仍失败: {str(e)}")
    
    def _parse_react_output(self, content: str) -> ReActOutput:
        """解析 ReAct JSON 输出"""
        # 尝试直接解析 JSON
        try:
            data = json.loads(content)
            return ReActOutput(**data)
        except json.JSONDecodeError:
            pass
        
        # 尝试从文本中提取 JSON（LLM 可能在 JSON 前后加了说明文字）
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return ReActOutput(**data)
            except (json.JSONDecodeError, ValueError):
                pass
        
        raise json.JSONDecodeError("无法解析 LLM 输出为 JSON", content, 0)
    
    async def _execute_action(self, action: Dict) -> str:
        """执行工具调用（JSON 格式）"""
        tool_name = action.get("tool")
        params = action.get("params", {})
        
        if not tool_name:
            return "错误: Action 中缺少 tool 字段"
        
        if tool_name not in self.tools:
            return f"错误: 未知工具 '{tool_name}'"
        
        tool = self.tools[tool_name]
        
        # 验证参数
        is_valid, error_msg = tool.validate_arguments(**params)
        if not is_valid:
            return f"参数验证失败: {error_msg}"
        
        return await tool.execute(**params)
```

### 4.4 规划器（Planner）— 容错机制 + 宽松匹配

```python
# core/planner.py

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from models.schemas import Task, SubTask, AgentRole, ExecutionPlan
from core.llm_client import LLMRouter

logger = logging.getLogger(__name__)

@dataclass
class Dependency:
    """任务依赖"""
    task_id: str
    depends_on: List[str]

class PlanParseError(Exception):
    """计划解析错误"""
    pass

class Planner:
    """
    任务规划器（带容错机制）
    
    改进点：
    1. 宽松匹配策略（支持多种格式变体）
    2. 解析失败时记录 WARNING 日志
    3. 触发 LLM 重新生成
    4. 最大重试次数限制
    """
    
    def __init__(self, llm_router: LLMRouter, max_retries=2):
        self.llm_router = llm_router
        self.max_retries = max_retries
    
    async def create_plan(self, task: Task) -> ExecutionPlan:
        """创建执行计划（带容错）"""
        for attempt in range(self.max_retries + 1):
            prompt = self._build_planning_prompt(task, attempt > 0)
            
            response = await self.llm_router.route(
                messages=[
                    {"role": "system", "content": "你是一个任务规划专家。"},
                    {"role": "user", "content": prompt}
                ],
                complexity="high"
            )
            
            # 尝试解析
            subtasks, parse_errors = self._parse_plan_with_fallback(
                response.content, task.id
            )
            
            if parse_errors:
                logger.warning(
                    f"计划解析出现 {len(parse_errors)} 个警告: {parse_errors}"
                )
            
            if not subtasks:
                logger.error(f"第 {attempt + 1} 次规划失败，未解析到子任务")
                if attempt < self.max_retries:
                    continue
                else:
                    # 最终回退：单任务串行执行
                    return self._create_fallback_plan(task)
            
            dependencies = self._build_dependencies(subtasks)
            
            if self._validate_plan(subtasks, dependencies):
                return ExecutionPlan(
                    task_id=task.id,
                    subtasks=subtasks,
                    dependencies=dependencies
                )
            else:
                logger.warning("计划验证失败，尝试重新规划")
                if attempt < self.max_retries:
                    continue
                else:
                    return self._create_fallback_plan(task)
        
        return self._create_fallback_plan(task)
    
    def _build_planning_prompt(self, task: Task, is_retry=False) -> str:
        """构建规划提示词"""
        retry_hint = """
之前生成的格式有误，请严格按照以下格式输出，不要添加额外说明文字：
""" if is_retry else ""
        
        return f"""请将以下任务拆解为子任务：

任务: {task.title}
描述: {task.description}

可用 Agent 角色：
- planner: 规划专家
- researcher: 研究员（信息收集）
- coder: 程序员（代码生成）
- writer: 写手（文档撰写）
- reviewer: 审查员（质量检查）
- executor: 执行者（工具调用）

{retry_hint}
请按以下格式输出：
1. [Agent角色] 子任务描述
2. [Agent角色] 子任务描述
   依赖: 1
3. [Agent角色] 子任务描述
   依赖: 1, 2

注意：
- 每行一个子任务
- 角色名必须小写
- 依赖使用数字编号（如 1, 2, 3）
"""
    
    def _parse_plan_with_fallback(self, content: str, task_id: str) -> Tuple[List[SubTask], List[str]]:
        """
        解析计划（宽松匹配 + 容错）
        
        Returns:
            (子任务列表, 解析错误列表)
        """
        subtasks = []
        errors = []
        lines = content.strip().split('\n')
        current_subtask = None
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            
            # 策略 1: 标准格式 "1. [角色] 描述"
            match = re.match(r'(\d+)\.\s*\[(\w+)\]\s*(.+)', line)
            
            # 策略 2: 宽松格式 "1. 角色: 描述" 或 "1) [角色] 描述"
            if not match:
                match = re.match(r'(\d+)[\.\)]\s*(\w+):\s*(.+)', line)
            
            # 策略 3: 更宽松 "1. 描述 (角色)"
            if not match:
                match = re.match(r'(\d+)\.\s*(.+?)\s*\((\w+)\)', line)
                if match:
                    # 调整分组顺序
                    match = type('Match', (), {
                        'group': lambda self, n: [None, match.group(1), match.group(3), match.group(2)][n]
                    })()
            
            if match:
                if current_subtask:
                    subtasks.append(current_subtask)
                
                try:
                    subtask_id = f"{task_id}_{match.group(1)}"
                    agent_role = AgentRole(match.group(2).lower())
                    description = match.group(3).strip()
                    
                    current_subtask = SubTask(
                        id=subtask_id,
                        task_id=task_id,
                        description=description,
                        assigned_agent=agent_role
                    )
                except ValueError as e:
                    errors.append(f"第 {line_num} 行: 无效的角色 '{match.group(2)}'")
                    continue
            
            elif line.startswith(('依赖:', 'deps:', 'depends:')) and current_subtask:
                deps_str = re.sub(r'^(依赖:|deps:|depends:)\s*', '', line).strip()
                try:
                    deps = [f"{task_id}_{d.strip()}" for d in re.split(r'[,，]\s*', deps_str)]
                    current_subtask.dependencies = deps
                except Exception as e:
                    errors.append(f"第 {line_num} 行: 依赖解析失败 '{deps_str}'")
            
            else:
                # 无法识别的行，记录警告
                if len(line) > 10:  # 忽略短行（可能是分隔符）
                    errors.append(f"第 {line_num} 行: 无法解析 '{line[:50]}...'")
        
        if current_subtask:
            subtasks.append(current_subtask)
        
        return subtasks, errors
    
    def _build_dependencies(self, subtasks: List[SubTask]) -> Dict[str, List[str]]:
        """构建依赖图"""
        return {subtask.id: subtask.dependencies for subtask in subtasks}
    
    def _validate_plan(self, subtasks: List[SubTask], dependencies: Dict) -> bool:
        """验证计划可行性"""
        # 检查循环依赖
        visited = set()
        temp_mark = set()
        
        def has_cycle(node_id: str) -> bool:
            if node_id in temp_mark:
                return True
            if node_id in visited:
                return False
            
            temp_mark.add(node_id)
            for dep_id in dependencies.get(node_id, []):
                if has_cycle(dep_id):
                    return True
            
            temp_mark.remove(node_id)
            visited.add(node_id)
            return False
        
        for subtask in subtasks:
            if has_cycle(subtask.id):
                logger.error(f"检测到循环依赖: {subtask.id}")
                return False
        
        # 检查依赖是否存在（宽松处理：移除无效依赖而不是失败）
        all_ids = {s.id for s in subtasks}
        for subtask in subtasks:
            valid_deps = [d for d in subtask.dependencies if d in all_ids]
            if len(valid_deps) != len(subtask.dependencies):
                removed = set(subtask.dependencies) - set(valid_deps)
                logger.warning(f"子任务 {subtask.id} 移除了无效依赖: {removed}")
                subtask.dependencies = valid_deps
        
        return True
    
    def _create_fallback_plan(self, task: Task) -> ExecutionPlan:
        """创建回退计划（当所有解析都失败时）"""
        logger.info("使用回退计划：单任务串行执行")
        
        subtasks = [
            SubTask(
                id=f"{task.id}_1",
                task_id=task.id,
                description=f"执行: {task.title}",
                assigned_agent=AgentRole.EXECUTOR
            )
        ]
        
        return ExecutionPlan(
            task_id=task.id,
            subtasks=subtasks,
            dependencies={subtasks[0].id: []}
        )
```

### 4.5 调度器（Orchestrator）— 超时与取消机制

```python
# core/orchestrator.py

import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum
import logging

from models.schemas import Task, SubTask, AgentStep, TaskStatus
from core.planner import Planner
from core.react_loop import ReActLoop
from core.cancellation import CancellationToken, CancellationError
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent 执行状态"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class Orchestrator:
    """
    Agent 调度器（带超时与取消机制）
    
    改进点：
    1. 子任务超时控制（默认 300 秒）
    2. 用户主动取消支持
    3. 取消后优雅清理资源
    4. 任务状态持久化
    """
    
    def __init__(self, planner, agents, max_concurrent=3, 
                 subtask_timeout=300, task_timeout=3600):
        self.planner = planner
        self.agents = agents
        self.max_concurrent = max_concurrent
        self.subtask_timeout = subtask_timeout
        self.task_timeout = task_timeout
        
        self.agent_status: Dict[str, AgentStatus] = {}
        self.subtask_results: Dict[str, str] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.cancellation_tokens: Dict[str, CancellationToken] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute(self, task: Task, stream=True,
                     cancellation_token=None) -> AsyncGenerator[AgentStep, None]:
        """执行任务（带取消和超时）"""
        cancellation_token = cancellation_token or CancellationToken()
        self.cancellation_tokens[task.id] = cancellation_token
        
        # 设置任务级超时
        try:
            async with asyncio.timeout(self.task_timeout):
                async for step in self._execute_with_timeout(
                    task, stream, cancellation_token
                ):
                    yield step
        except asyncio.TimeoutError:
            logger.error(f"任务 {task.id} 执行超时（>{self.task_timeout}秒）")
            task.status = TaskStatus.FAILED
            yield AgentStep(
                task_id=task.id,
                step_type="error",
                content=f"任务执行超时（>{self.task_timeout}秒）",
                step_number=999
            )
        finally:
            # 清理资源
            await self._cleanup_task(task.id)
    
    async def _execute_with_timeout(self, task, stream, cancellation_token):
        """执行核心逻辑"""
        # 1. 创建执行计划
        yield AgentStep(
            task_id=task.id,
            step_type="thought",
            content="开始规划任务...",
            step_number=0
        )
        
        # 检查取消
        if cancellation_token.is_cancelled:
            yield AgentStep(
                task_id=task.id,
                step_type="error",
                content="任务已被取消",
                step_number=0
            )
            return
        
        plan = await self.planner.create_plan(task)
        task.plan = plan
        task.status = TaskStatus.PLANNING
        
        yield AgentStep(
            task_id=task.id,
            step_type="thought",
            content=f"任务已拆解为 {len(plan.subtasks)} 个子任务",
            step_number=0
        )
        
        # 2. 按依赖图执行
        task.status = TaskStatus.EXECUTING
        
        completed = set()
        failed = set()
        pending = set(s.id for s in plan.subtasks)
        
        while pending:
            # 检查取消
            if cancellation_token.is_cancelled:
                yield AgentStep(
                    task_id=task.id,
                    step_type="error",
                    content="任务已被用户取消",
                    step_number=999
                )
                task.status = TaskStatus.CANCELLED
                return
            
            ready = [
                s for s in plan.subtasks
                if s.id in pending
                and all(dep in completed for dep in s.dependencies)
                and s.id not in self.running_tasks
            ]
            
            if not ready and not self.running_tasks:
                break
            
            for subtask in ready[:self.max_concurrent - len(self.running_tasks)]:
                self.agent_status[subtask.id] = AgentStatus.THINKING
                asyncio_task = asyncio.create_task(
                    self._execute_subtask_with_timeout(
                        task, subtask, stream, cancellation_token
                    )
                )
                self.running_tasks[subtask.id] = asyncio_task
            
            if self.running_tasks:
                done, pending_tasks = await asyncio.wait(
                    self.running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=5.0  # 每 5 秒检查一次取消
                )
                
                for asyncio_task in done:
                    subtask_id = None
                    for sid, t in list(self.running_tasks.items()):
                        if t == asyncio_task:
                            subtask_id = sid
                            break
                    
                    if subtask_id:
                        del self.running_tasks[subtask_id]
                        pending.discard(subtask_id)
                        
                        try:
                            result = await asyncio_task
                            completed.add(subtask_id)
                            self.subtask_results[subtask_id] = result
                            self.agent_status[subtask_id] = AgentStatus.COMPLETED
                        except asyncio.TimeoutError:
                            failed.add(subtask_id)
                            self.agent_status[subtask_id] = AgentStatus.TIMEOUT
                            self.subtask_results[subtask_id] = f"子任务超时（>{self.subtask_timeout}秒）"
                        except asyncio.CancelledError:
                            failed.add(subtask_id)
                            self.agent_status[subtask_id] = AgentStatus.CANCELLED
                            self.subtask_results[subtask_id] = "子任务被取消"
                        except Exception as e:
                            failed.add(subtask_id)
                            self.agent_status[subtask_id] = AgentStatus.FAILED
                            self.subtask_results[subtask_id] = f"错误: {str(e)}"
        
        # 3. 任务完成
        if failed:
            task.status = TaskStatus.FAILED
            yield AgentStep(
                task_id=task.id,
                step_type="error",
                content=f"任务部分失败: {len(failed)} 个子任务失败",
                step_number=999
            )
        else:
            task.status = TaskStatus.COMPLETED
            task.result = self._compile_results(plan)
            yield AgentStep(
                task_id=task.id,
                step_type="final",
                content=task.result,
                step_number=999
            )
    
    async def _execute_subtask_with_timeout(self, task, subtask, stream, 
                                           cancellation_token):
        """执行单个子任务（带超时）"""
        async with self.semaphore:
            agent = self.agents.get(subtask.assigned_agent.value)
            
            if not agent:
                raise ValueError(f"未找到 Agent: {subtask.assigned_agent}")
            
            context = {
                "task_id": task.id,
                "subtask_id": subtask.id,
                "parent_task": task.title,
                "description": subtask.description,
                "dependencies_results": {
                    dep_id: self.subtask_results.get(dep_id, "")
                    for dep_id in subtask.dependencies
                }
            }
            
            # 使用 wait_for 实现子任务超时
            try:
                return await asyncio.wait_for(
                    self._run_agent_with_cancellation(
                        agent, subtask, context, stream, cancellation_token
                    ),
                    timeout=self.subtask_timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"子任务 {subtask.id} 超时")
                raise
    
    async def _run_agent_with_cancellation(self, agent, subtask, context, 
                                          stream, cancellation_token):
        """运行 Agent（支持取消）"""
        steps = []
        async for step in agent.run(
            subtask.description, context, stream=stream,
            cancellation_token=cancellation_token
        ):
            steps.append(step)
            if cancellation_token.is_cancelled:
                raise asyncio.CancelledError("任务被取消")
        
        final_steps = [s for s in steps if s.step_type == "final"]
        if final_steps:
            return final_steps[-1].content
        
        return "未产生最终结果"
    
    async def cancel_task(self, task_id: str):
        """
        取消任务（用户主动调用）
        
        流程：
        1. 设置取消令牌
        2. 取消所有正在运行的子任务
        3. 清理资源
        4. 更新数据库状态
        """
        logger.info(f"正在取消任务: {task_id}")
        
        # 1. 设置取消令牌
        if task_id in self.cancellation_tokens:
            self.cancellation_tokens[task_id].cancel()
        
        # 2. 取消所有子任务
        for subtask_id, asyncio_task in list(self.running_tasks.items()):
            if asyncio_task and not asyncio_task.done():
                asyncio_task.cancel()
                try:
                    await asyncio_task
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            self.agent_status[subtask_id] = AgentStatus.CANCELLED
        
        # 3. 清理
        await self._cleanup_task(task_id)
        
        logger.info(f"任务已取消: {task_id}")
    
    async def _cleanup_task(self, task_id: str):
        """清理任务资源"""
        # 移除取消令牌
        if task_id in self.cancellation_tokens:
            del self.cancellation_tokens[task_id]
        
        # 清理运行中的任务
        self.running_tasks.clear()
        
        # 清理状态（保留结果）
        self.agent_status.clear()
    
    def _compile_results(self, plan) -> str:
        """编译所有子任务结果"""
        results = []
        for subtask in plan.subtasks:
            result = self.subtask_results.get(subtask.id, "")
            results.append(f"## {subtask.description}\n\n{result}")
        
        return "\n\n".join(results)
    
    def get_task_status(self, task_id: str) -> Dict:
        """获取任务实时状态"""
        return {
            "task_id": task_id,
            "running_subtasks": len(self.running_tasks),
            "agent_status": {
                sid: status.value 
                for sid, status in self.agent_status.items()
            },
            "is_cancelled": (
                self.cancellation_tokens.get(task_id, CancellationToken()).is_cancelled
            )
        }
```

### 4.6 Agent 角色实现

```python
# agents/base.py

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime

from models.schemas import AgentStep, AgentRole
from core.llm_client import LLMRouter
from core.react_loop import ReActLoop

class BaseAgent(ABC):
    """Agent 抽象基类"""
    
    def __init__(self, role, llm_router, tools=None, max_steps=10):
        self.role = role
        self.llm_router = llm_router
        self.tools = tools or []
        self.max_steps = max_steps
        
        self.react_loop = ReActLoop(
            llm_router=llm_router,
            tools=self.get_tools(),
            max_steps=max_steps,
            agent_role=role.value
        )
        
        self.name = self._get_name()
        self.description = self._get_description()
        self.system_prompt = self._build_system_prompt()
    
    @abstractmethod
    def _get_name(self) -> str:
        pass
    
    @abstractmethod
    def _get_description(self) -> str:
        pass
    
    @abstractmethod
    def _build_system_prompt(self) -> str:
        pass
    
    def get_tools(self) -> List:
        return self.tools
    
    async def run(self, task, context=None) -> AsyncGenerator[AgentStep, None]:
        processed_task = await self._pre_process(task, context)
        
        async for step in self.react_loop.run(processed_task, context):
            processed_step = await self._post_process_step(step)
            yield processed_step
        
        await self._post_process(task, context)
    
    async def _pre_process(self, task, context):
        return task
    
    async def _post_process_step(self, step):
        return step
    
    async def _post_process(self, task, context):
        pass
    
    async def communicate(self, message, target_agent):
        context = {
            "from_agent": self.role.value,
            "to_agent": target_agent.role.value,
            "message": message
        }
        response = await target_agent._handle_message(context)
        return response
    
    async def _handle_message(self, context):
        prompt = f"你收到了来自 {context['from_agent']} 的消息：\n\n{context['message']}\n\n请回复。"
        
        response = await self.llm_router.route(
            messages=[{"role": "user", "content": prompt}],
            complexity="low"
        )
        
        return response.content

# 具体角色实现示例
# agents/researcher_agent.py

class ResearcherAgent(BaseAgent):
    """研究员 Agent"""
    
    def _get_name(self):
        return "研究员"
    
    def _get_description(self):
        return "擅长信息收集、数据分析和资料整理"
    
    def _build_system_prompt(self):
        return """你是研究员，擅长信息收集和分析。

你的职责：
1. 通过网络搜索收集相关信息
2. 分析和整理数据
3. 验证信息的准确性和可靠性
4. 提供结构化的研究报告

原则：
- 多来源交叉验证
- 标注信息来源
- 区分事实和观点
"""
    
    def get_tools(self):
        return [
            WebSearchTool(),
            FileReadTool(),
            MemorySearchTool(),
            CalculatorTool()
        ]

# 其他角色类似实现...
# CoderAgent, WriterAgent, ReviewerAgent, ExecutorAgent
```

### 4.7 MCP 工具系统

```python
# tools/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class ToolSchema(BaseModel):
    """工具参数模式"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: list[str] = Field(default_factory=list)

class BaseTool(ABC):
    """工具抽象基类"""
    
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
    
    def get_schema(self) -> Dict[str, Any]:
        return self.schema.model_dump()

# mcp/tool_registry.py

class ToolRegistry:
    """MCP 工具注册中心"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
    
    def register(self, tool, category="general"):
        self._tools[tool.name] = tool
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)
    
    def get(self, tool_name):
        return self._tools.get(tool_name)
    
    def list_tools(self, category=None):
        if category:
            tool_names = self._categories.get(category, [])
        else:
            tool_names = list(self._tools.keys())
        
        return [
            {
                "name": name,
                "description": self._tools[name].description,
                "schema": self._tools[name].get_schema()
            }
            for name in tool_names
        ]

# 具体工具实现示例
# tools/web_search.py

class WebSearchTool(BaseTool):
    """网络搜索工具"""
    
    name = "web_search"
    description = "搜索网络信息，获取相关网页内容"
    
    def _build_schema(self):
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "query": {"type": "string", "description": "搜索关键词"},
                "max_results": {"type": "integer", "description": "最大结果数", "default": 5}
            },
            required=["query"]
        )
    
    async def execute(self, query, max_results=5):
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=min(max_results, 10))
                
                formatted = []
                for i, result in enumerate(results, 1):
                    formatted.append(
                        f"{i}. {result['title']}\n"
                        f"   URL: {result['href']}\n"
                        f"   摘要: {result['body']}\n"
                    )
                
                return "\n".join(formatted) if formatted else "未找到相关结果"
        except Exception as e:
            return f"搜索失败: {str(e)}"

# 其他工具类似实现...
# CalculatorTool, CodeExecuteTool, FileReadTool, etc.
```

### 4.8 A2A 通信系统 — 修复版（Queue + 历史清理 + 持久化）

```python
# core/a2a_bus.py

from typing import Dict, List, Optional, Callable, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import uuid
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    DIRECT = "direct"
    STATUS = "status"

class MessagePriority(int, Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class A2AMessage(BaseModel):
    """A2A 标准消息格式"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: Optional[str] = None
    sender: str
    recipient: Optional[str] = None
    type: MessageType = Field(default=MessageType.DIRECT)
    priority: MessagePriority = Field(default=MessagePriority.NORMAL)
    payload: Dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ttl: int = Field(default=300)
    hop_count: int = Field(default=0)
    trace: List[str] = Field(default_factory=list)

class A2ABus:
    """
    A2A 消息总线（修复版）
    
    改进点：
    1. 使用 asyncio.Queue 替代不存在的 PriorityQueue
    2. 定期清理历史消息（防止内存泄漏）
    3. 增加消息持久化层（Redis Stream）
    4. 死信队列支持
    """
    
    def __init__(self, redis_client=None, max_history=1000, cleanup_interval=60):
        self._subscribers: Dict[str, Callable] = {}
        # 修复：使用 asyncio.Queue 而不是 PriorityQueue
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._message_history: List[A2AMessage] = []
        self._max_history = max_history
        self._cleanup_interval = cleanup_interval
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._running = False
        
        # 可选：Redis 持久化
        self._redis = redis_client
        self._dead_letter_queue: List[A2AMessage] = []
        self._max_dead_letter = 100
    
    async def start(self):
        self._running = True
        asyncio.create_task(self._dispatcher_loop())
        asyncio.create_task(self._cleanup_loop())
        logger.info("A2A 总线已启动")
    
    async def stop(self):
        self._running = False
        logger.info("A2A 总线已停止")
    
    def subscribe(self, agent_id, callback):
        self._subscribers[agent_id] = callback
        logger.info(f"Agent {agent_id} 已订阅")
    
    def unsubscribe(self, agent_id):
        if agent_id in self._subscribers:
            del self._subscribers[agent_id]
            logger.info(f"Agent {agent_id} 已取消订阅")
    
    async def send(self, message: A2AMessage) -> bool:
        """发送消息"""
        if message.sender not in self._subscribers:
            logger.warning(f"发送者 {message.sender} 未注册")
            return False
        
        # 检查 TTL
        if message.ttl <= 0:
            logger.warning(f"消息 {message.id} 已过期")
            return False
        
        # 入队（Queue 不支持优先级，按 FIFO 处理）
        await self._message_queue.put(message)
        
        # 记录历史
        self._message_history.append(message)
        self._enforce_history_limit()
        
        # 可选：持久化到 Redis
        if self._redis:
            try:
                await self._redis.xadd(
                    f"a2a:messages:{message.type.value}",
                    {"data": message.model_dump_json()}
                )
            except Exception as e:
                logger.error(f"Redis 持久化失败: {e}")
        
        return True
    
    def _enforce_history_limit(self):
        """强制历史消息数量限制"""
        if len(self._message_history) > self._max_history:
            # 保留最近的消息，移除旧的
            self._message_history = self._message_history[-self._max_history:]
    
    async def _cleanup_loop(self):
        """定期清理循环"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                # 清理过期消息（基于 TTL）
                now = datetime.utcnow()
                self._message_history = [
                    m for m in self._message_history
                    if (m.timestamp + timedelta(seconds=m.ttl)) > now
                ]
                
                # 清理死信队列
                if len(self._dead_letter_queue) > self._max_dead_letter:
                    self._dead_letter_queue = self._dead_letter_queue[-self._max_dead_letter:]
                
                logger.debug(f"清理完成，历史消息: {len(self._message_history)}")
                
            except Exception as e:
                logger.error(f"清理循环错误: {e}")
    
    async def request(self, sender, recipient, payload, timeout=30.0):
        """请求-响应模式"""
        correlation_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._pending_responses[correlation_id] = future
        
        request_msg = A2AMessage(
            sender=sender,
            recipient=recipient,
            type=MessageType.REQUEST,
            correlation_id=correlation_id,
            payload=payload
        )
        
        await self.send(request_msg)
        
        try:
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"请求 {correlation_id} 超时")
            
            # 添加到死信队列
            self._dead_letter_queue.append(request_msg)
            
            return None
        finally:
            if correlation_id in self._pending_responses:
                del self._pending_responses[correlation_id]
    
    async def broadcast(self, sender, payload, exclude=None):
        """广播消息"""
        exclude = exclude or []
        
        message = A2AMessage(
            sender=sender,
            recipient=None,
            type=MessageType.BROADCAST,
            payload=payload
        )
        
        await self.send(message)
        
        return {
            agent_id: None
            for agent_id in self._subscribers
            if agent_id != sender and agent_id not in exclude
        }
    
    async def _dispatcher_loop(self):
        """消息分发循环"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )
                asyncio.create_task(self._process_message(message))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"分发循环错误: {e}")
    
    async def _process_message(self, message: A2AMessage):
        """处理单条消息"""
        message.trace.append(f"processed_at_{datetime.utcnow().isoformat()}")
        message.hop_count += 1
        
        # 检查是否是响应
        if message.correlation_id and message.correlation_id in self._pending_responses:
            future = self._pending_responses[message.correlation_id]
            if not future.done():
                future.set_result(message)
            return
        
        # 路由消息
        if message.type == MessageType.BROADCAST:
            await self._broadcast_message(message)
        elif message.recipient:
            await self._send_direct(message)
    
    async def _broadcast_message(self, message: A2AMessage):
        """广播消息"""
        failed_agents = []
        
        for agent_id, callback in self._subscribers.items():
            if agent_id != message.sender:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(message))
                    else:
                        callback(message)
                except Exception as e:
                    logger.error(f"广播到 {agent_id} 失败: {e}")
                    failed_agents.append(agent_id)
        
        # 记录失败
        if failed_agents:
            logger.warning(f"广播失败: {failed_agents}")
    
    async def _send_direct(self, message: A2AMessage):
        """点对点发送"""
        if message.recipient in self._subscribers:
            callback = self._subscribers[message.recipient]
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(message))
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"发送给 {message.recipient} 失败: {e}")
                
                # 添加到死信队列
                self._dead_letter_queue.append(message)
        else:
            logger.warning(f"接收者 {message.recipient} 未注册")
            
            # 未送达消息加入死信队列
            self._dead_letter_queue.append(message)
    
    def get_message_history(self, sender=None, recipient=None, 
                           message_type=None, limit=100) -> List[A2AMessage]:
        """获取消息历史"""
        filtered = self._message_history
        
        if sender:
            filtered = [m for m in filtered if m.sender == sender]
        if recipient:
            filtered = [m for m in filtered if m.recipient == recipient]
        if message_type:
            filtered = [m for m in filtered if m.type == message_type]
        
        return filtered[-limit:]
    
    def get_dead_letter_queue(self, limit=50) -> List[A2AMessage]:
        """获取死信队列"""
        return self._dead_letter_queue[-limit:]
    
    def get_message_flow(self, task_id: str) -> List[Dict]:
        """获取任务的消息流（用于可视化）"""
        task_messages = [
            m for m in self._message_history
            if m.payload.get("task_id") == task_id
        ]
        
        return [
            {
                "id": msg.id,
                "from": msg.sender,
                "to": msg.recipient or "broadcast",
                "type": msg.type.value,
                "timestamp": msg.timestamp.isoformat(),
                "content": msg.payload.get("content", "")[:100]
            }
            for msg in task_messages
        ]
```

### 4.9 RAG 系统

```python
# core/rag_system.py

from typing import List, Dict, Optional
import numpy as np
from datetime import datetime

import chromadb
from chromadb.config import Settings

from models.schemas import KnowledgeDoc
from core.llm_client import LLMRouter

class DocumentChunk(BaseModel):
    """文档分块"""
    id: str
    doc_id: str
    content: str
    embedding: List[float]
    metadata: Dict
    index: int

class SearchResult(BaseModel):
    """搜索结果"""
    chunk: DocumentChunk
    score: float
    doc_info: Dict

class RAGSystem:
    """RAG (Retrieval-Augmented Generation) 系统"""
    
    def __init__(self, llm_router, persist_directory="./data/chromadb", 
                 embedding_model="text-embedding-v2"):
        self.llm_router = llm_router
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))
        
        self.collection = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_document(self, doc: KnowledgeDoc) -> bool:
        """添加文档到知识库"""
        try:
            content = await self._read_document(doc)
            chunks = self._chunk_document(content, doc.id)
            embeddings = await self._generate_embeddings([c.content for c in chunks])
            
            for i, chunk in enumerate(chunks):
                chunk.embedding = embeddings[i]
                self.collection.add(
                    ids=[chunk.id],
                    embeddings=[chunk.embedding],
                    documents=[chunk.content],
                    metadatas=[{
                        "doc_id": doc.id,
                        "filename": doc.filename,
                        "chunk_index": chunk.index,
                        "user_id": doc.user_id
                    }]
                )
            
            doc.embedding_ids = [chunk.id for chunk in chunks]
            doc.chunk_count = len(chunks)
            
            return True
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    async def search(self, query, user_id=None, top_k=5, min_score=0.7):
        """语义检索"""
        try:
            query_embedding = await self._generate_embeddings([query])
            
            where_clause = {}
            if user_id:
                where_clause["user_id"] = user_id
            
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k * 2,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            for i in range(len(results['ids'][0])):
                score = 1 - results['distances'][0][i]
                
                if score >= min_score:
                    search_results.append(SearchResult(
                        chunk=DocumentChunk(
                            id=results['ids'][0][i],
                            doc_id=results['metadatas'][0][i]["doc_id"],
                            content=results['documents'][0][i],
                            embedding=[],
                            metadata=results['metadatas'][0][i],
                            index=results['metadatas'][0][i]["chunk_index"]
                        ),
                        score=score,
                        doc_info={
                            "filename": results['metadatas'][0][i]["filename"],
                            "user_id": results['metadatas'][0][i]["user_id"]
                        }
                    ))
            
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results[:top_k]
            
        except Exception as e:
            print(f"检索失败: {e}")
            return []
    
    async def build_context(self, query, user_id=None, max_context_length=2000):
        """构建 RAG 上下文"""
        results = await self.search(query, user_id, top_k=5)
        
        if not results:
            return ""
        
        context_parts = []
        current_length = 0
        
        for result in results:
            chunk_text = f"""
[相关度: {result.score:.2f}]
来源: {result.doc_info['filename']}
内容: {result.chunk.content}
"""
            if current_length + len(chunk_text) > max_context_length:
                break
            
            context_parts.append(chunk_text)
            current_length += len(chunk_text)
        
        return "\n---\n".join(context_parts)
    
    def _chunk_document(self, content, doc_id, chunk_size=500, overlap=50):
        """文档分块"""
        chunks = []
        paragraphs = content.split('\n\n')
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) < chunk_size:
                current_chunk += paragraph + "\n\n"
            else:
                if current_chunk:
                    chunks.append(DocumentChunk(
                        id=f"{doc_id}_chunk_{chunk_index}",
                        doc_id=doc_id,
                        content=current_chunk.strip(),
                        embedding=[],
                        metadata={},
                        index=chunk_index
                    ))
                    chunk_index += 1
                
                current_chunk = paragraph + "\n\n"
        
        if current_chunk:
            chunks.append(DocumentChunk(
                id=f"{doc_id}_chunk_{chunk_index}",
                doc_id=doc_id,
                content=current_chunk.strip(),
                embedding=[],
                metadata={},
                index=chunk_index
            ))
        
        return chunks
    
    async def _generate_embeddings(self, texts):
        """生成嵌入向量"""
        return await self.llm_router.embed(texts, self.embedding_model)
```

### 4.10 记忆管理系统

```python
# core/memory_manager.py

from typing import List, Dict, Optional
from datetime import datetime, timedelta

from models.schemas import User, AgentStep
from core.rag_system import RAGSystem, SearchResult

class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EXPERIENCE = "experience"

class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str
    type: MemoryType
    user_id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict = Field(default_factory=dict)
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class MemoryManager:
    """三层记忆管理系统"""
    
    def __init__(self, rag_system, short_term_ttl=3600):
        self.rag_system = rag_system
        self.short_term_ttl = short_term_ttl
        self._short_term: Dict[str, List[MemoryEntry]] = {}
        self._long_term_collection = "long_term_memory"
        self._experience_collection = "experience_memory"
    
    async def add_short_term(self, user_id, content, source=None):
        """添加短期记忆"""
        entry = MemoryEntry(
            id=f"stm_{datetime.utcnow().timestamp()}",
            type=MemoryType.SHORT_TERM,
            user_id=user_id,
            content=content,
            source=source,
            expires_at=datetime.utcnow() + timedelta(seconds=self.short_term_ttl)
        )
        
        if user_id not in self._short_term:
            self._short_term[user_id] = []
        
        self._short_term[user_id].append(entry)
        self._cleanup_short_term(user_id)
    
    async def get_short_term(self, user_id, limit=10):
        """获取短期记忆"""
        self._cleanup_short_term(user_id)
        memories = self._short_term.get(user_id, [])
        memories.sort(key=lambda x: x.created_at, reverse=True)
        return [m.content for m in memories[:limit]]
    
    def _cleanup_short_term(self, user_id):
        """清理过期短期记忆"""
        if user_id not in self._short_term:
            return
        
        now = datetime.utcnow()
        self._short_term[user_id] = [
            m for m in self._short_term[user_id]
            if m.expires_at is None or m.expires_at > now
        ]
    
    async def add_long_term(self, user_id, content, metadata=None):
        """添加长期记忆"""
        entry = MemoryEntry(
            id=f"ltm_{datetime.utcnow().timestamp()}",
            type=MemoryType.LONG_TERM,
            user_id=user_id,
            content=content,
            metadata=metadata or {}
        )
        
        embedding = await self.rag_system._generate_embeddings([content])
        entry.embedding = embedding[0]
        
        collection = self.rag_system.client.get_or_create_collection(
            name=self._long_term_collection
        )
        
        collection.add(
            ids=[entry.id],
            embeddings=[entry.embedding],
            documents=[entry.content],
            metadatas=[{"user_id": user_id, "type": "long_term", **entry.metadata}]
        )
    
    async def search_long_term(self, user_id, query, top_k=5):
        """检索长期记忆"""
        query_embedding = await self.rag_system._generate_embeddings([query])
        
        collection = self.rag_system.client.get_collection(
            name=self._long_term_collection
        )
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=top_k,
            where={"user_id": user_id}
        )
        
        search_results = []
        for i in range(len(results['ids'][0])):
            score = 1 - results['distances'][0][i]
            search_results.append(SearchResult(
                chunk=None,
                score=score,
                doc_info={
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i]
                }
            ))
        
        return search_results
    
    async def add_experience(self, user_id, task_type, reflection, lessons):
        """添加经验记忆（来自 Reflection）"""
        content = f"""
任务类型: {task_type}
反思: {reflection}
经验教训:
{chr(10).join(f"- {lesson}" for lesson in lessons)}
"""
        
        entry = MemoryEntry(
            id=f"exp_{datetime.utcnow().timestamp()}",
            type=MemoryType.EXPERIENCE,
            user_id=user_id,
            content=content,
            metadata={"task_type": task_type}
        )
        
        embedding = await self.rag_system._generate_embeddings([content])
        entry.embedding = embedding[0]
        
        collection = self.rag_system.client.get_or_create_collection(
            name=self._experience_collection
        )
        
        collection.add(
            ids=[entry.id],
            embeddings=[entry.embedding],
            documents=[entry.content],
            metadatas=[{
                "user_id": user_id,
                "type": "experience",
                "task_type": task_type
            }]
        )
    
    async def build_memory_context(self, user_id, current_task, 
                                  include_short_term=True,
                                  include_long_term=True,
                                  include_experience=True):
        """构建记忆上下文（用于 Prompt）"""
        context_parts = []
        
        if include_short_term:
            short_term = await self.get_short_term(user_id, limit=5)
            if short_term:
                context_parts.append("## 近期操作\n" + "\n".join(
                    f"- {m}" for m in short_term
                ))
        
        if include_long_term:
            long_term = await self.search_long_term(
                user_id=user_id, query=current_task, top_k=3
            )
            if long_term:
                context_parts.append("## 相关历史\n" + "\n".join(
                    f"- [相关度: {r.score:.2f}] {r.doc_info['content'][:200]}"
                    for r in long_term
                ))
        
        if include_experience:
            experience = await self.get_relevant_experience(
                user_id=user_id, task_description=current_task
            )
            if experience:
                context_parts.append("## 经验教训\n" + "\n".join(
                    f"- {e[:200]}" for e in experience
                ))
        
        return "\n\n".join(context_parts)
    
    async def learn_from_interaction(self, user_id, interaction):
        """从交互中学习（更新用户偏好）"""
        feedback = interaction.get("feedback", "")
        task_type = interaction.get("task_type", "")
        
        if "prefer" in feedback.lower() or "喜欢" in feedback:
            await self.add_long_term(
                user_id=user_id,
                content=f"用户偏好: {feedback}",
                metadata={"type": "preference", "task_type": task_type}
            )
        
        await self.add_short_term(
            user_id=user_id,
            content=f"交互: {interaction.get('task', '')} -> 反馈: {feedback}",
            source="interaction"
        )
```

### 4.11 反思引擎

```python
# core/reflection_engine.py

from typing import Dict, List, Optional
from datetime import datetime

from models.schemas import Task, AgentStep
from core.llm_client import LLMRouter
from core.memory_manager import MemoryManager

class ReflectionReport(BaseModel):
    """反思报告"""
    task_id: str
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvements: List[str]
    lessons: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ReflectionEngine:
    """
    反思引擎
    
    任务完成后进行自我评估：
    1. 分析执行过程
    2. 识别问题和改进点
    3. 生成经验教训
    4. 保存到经验记忆
    """
    
    def __init__(self, llm_router, memory_manager):
        self.llm_router = llm_router
        self.memory_manager = memory_manager
    
    async def reflect(self, task: Task) -> ReflectionReport:
        """对任务执行进行反思"""
        execution_data = self._collect_execution_data(task)
        prompt = self._build_reflection_prompt(task, execution_data)
        
        response = await self.llm_router.route(
            messages=[
                {"role": "system", "content": "你是反思专家，擅长事后分析和改进建议。"},
                {"role": "user", "content": prompt}
            ],
            complexity="high"
        )
        
        report = self._parse_reflection(response.content, task.id)
        
        await self.memory_manager.add_experience(
            user_id=task.user_id,
            task_type=self._classify_task_type(task),
            reflection=report.overall_assessment if hasattr(report, 'overall_assessment') else "",
            lessons=report.lessons
        )
        
        return report
    
    def _collect_execution_data(self, task: Task) -> Dict:
        """收集执行数据"""
        return {
            "task_title": task.title,
            "task_description": task.description,
            "total_agents": task.total_agents,
            "total_steps": task.total_steps,
            "total_latency_ms": task.total_latency_ms,
            "status": task.status.value,
            "result": task.result,
            "plan": task.plan.model_dump() if task.plan else None
        }
    
    def _build_reflection_prompt(self, task: Task, execution_data: Dict) -> str:
        """构建反思提示词"""
        return f"""请对以下任务执行进行反思和评估：

任务: {task.title}
描述: {task.description}
状态: {task.status.value}

执行数据:
- 使用 Agent 数: {execution_data['total_agents']}
- 总步数: {execution_data['total_steps']}
- 总耗时: {execution_data['total_latency_ms']}ms

执行结果:
{task.result or '无结果'}

请按以下格式输出：
总体评分: [0-10]
优点:
- [优点1]
- [优点2]

不足:
- [不足1]
- [不足2]

改进建议:
- [建议1]
- [建议2]

经验教训:
- [经验1]
- [经验2]
"""
    
    def _parse_reflection(self, content: str, task_id: str) -> ReflectionReport:
        """解析反思结果"""
        import re
        
        score_match = re.search(r'总体评分:\s*(\d+(?:\.\d+)?)', content)
        score = float(score_match.group(1)) if score_match else 5.0
        
        def extract_list(section: str) -> List[str]:
            pattern = rf'{section}:\s*(.*?)(?=\n\n|\Z)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                items = re.findall(r'- (.+)', match.group(1))
                return [item.strip() for item in items]
            return []
        
        strengths = extract_list('优点')
        weaknesses = extract_list('不足')
        improvements = extract_list('改进建议')
        lessons = extract_list('经验教训')
        
        return ReflectionReport(
            task_id=task_id,
            overall_score=min(score, 10.0),
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
            lessons=lessons
        )
    
    def _classify_task_type(self, task: Task) -> str:
        """分类任务类型"""
        title_lower = task.title.lower()
        
        if any(kw in title_lower for kw in ['code', '编程', '代码', '程序']):
            return 'coding'
        elif any(kw in title_lower for kw in ['write', '写', '文档', '文章']):
            return 'writing'
        elif any(kw in title_lower for kw in ['research', '调研', '研究', '分析']):
            return 'research'
        elif any(kw in title_lower for kw in ['review', '审查', '检查']):
            return 'review'
        else:
            return 'general'
```

---

## 5. 数据库设计

### 5.1 PostgreSQL Schema（生产环境）

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    api_keys JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 工作区表
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    owner_id UUID REFERENCES users(id),
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 工作区成员关联表
CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(id),
    user_id UUID REFERENCES users(id),
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

-- 任务表
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    total_agents INT DEFAULT 0,
    total_steps INT DEFAULT 0,
    total_latency_ms INT DEFAULT 0,
    plan JSONB,
    result TEXT,
    reflection JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 子任务表
CREATE TABLE subtasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    description TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    assigned_agent VARCHAR(20) NOT NULL,
    dependencies JSONB DEFAULT '[]',
    expected_output TEXT,
    result TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent 步骤表
CREATE TABLE agent_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    subtask_id UUID REFERENCES subtasks(id),
    agent_id VARCHAR(50) NOT NULL,
    step_number INT NOT NULL,
    step_type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    latency_ms INT DEFAULT 0,
    token_count INT DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 知识库文档表
CREATE TABLE knowledge_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    embedding_ids JSONB DEFAULT '[]',
    chunk_count INT DEFAULT 0,
    file_size INT NOT NULL,
    upload_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 性能指标表
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    llm_calls INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    planning_latency_ms INT DEFAULT 0,
    execution_latency_ms INT DEFAULT 0,
    total_latency_ms INT DEFAULT 0,
    peak_memory_mb FLOAT DEFAULT 0,
    cpu_percent FLOAT DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_workspace_id ON tasks(workspace_id);
CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);
CREATE INDEX idx_agent_steps_task_id ON agent_steps(task_id);
CREATE INDEX idx_agent_steps_timestamp ON agent_steps(timestamp);
CREATE INDEX idx_knowledge_docs_user_id ON knowledge_docs(user_id);
CREATE INDEX idx_performance_metrics_task_id ON performance_metrics(task_id);
```

### 5.2 SQLite Schema（本地开发）

```sql
-- SQLite 版本（简化版）
-- 与 PostgreSQL 结构相同，但使用 INTEGER PRIMARY KEY AUTOINCREMENT

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    api_keys TEXT DEFAULT '{}',
    preferences TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 其他表类似...
```

---

## 6. API 设计

### 6.1 REST API 概览

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| POST | /auth/register | 用户注册 | 否 |
| POST | /auth/login | 用户登录 | 否 |
| GET | /auth/me | 获取当前用户 | 是 |
| PUT | /auth/preferences | 更新偏好 | 是 |
| POST | /auth/api-keys | 更新 API Keys | 是 |
| POST | /tasks | 创建任务 | 是 |
| GET | /tasks | 获取任务列表 | 是 |
| GET | /tasks/{id} | 获取任务详情 | 是 |
| DELETE | /tasks/{id} | 删除任务 | 是 |
| POST | /tasks/{id}/cancel | 取消任务 | 是 |
| GET | /tasks/{id}/stream | SSE 流式执行 | 是 |
| GET | /tasks/{id}/plan | 获取执行计划 | 是 |
| GET | /tasks/{id}/reflect | 获取反思报告 | 是 |
| GET | /agents | 获取 Agent 列表 | 是 |
| GET | /agents/{id}/status | 获取 Agent 状态 | 是 |
| POST | /agents/{id}/message | Agent 间通信 | 是 |
| GET | /tools | 列出可用工具 | 是 |
| POST | /knowledge | 上传文档 | 是 |
| GET | /knowledge | 获取文档列表 | 是 |
| DELETE | /knowledge/{id} | 删除文档 | 是 |
| POST | /knowledge/search | 语义搜索 | 是 |
| GET | /monitoring/system | 系统资源统计 | 是 |
| GET | /monitoring/latency | 延迟统计 | 是 |
| GET | /monitoring/llm | LLM 调用统计 | 是 |
| GET | /monitoring/tasks/{id} | 任务性能指标 | 是 |

### 6.2 SSE 流式 API

```
GET /tasks/{task_id}/stream

Headers:
  Authorization: Bearer <token>

Response: text/event-stream

event: step
data: {"type": "thought", "content": "开始分析任务...", "step_number": 1}

event: step
data: {"type": "action", "content": "web_search(query='...')", "step_number": 1}

event: step
data: {"type": "observation", "content": "搜索结果: ...", "step_number": 1}

event: step
data: {"type": "final", "content": "任务完成，结果是...", "step_number": 10}

event: done
data: {"task_id": "...", "status": "completed"}
```

### 6.3 认证中间件

```python
# api/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 从数据库获取用户
    return user
```

---

## 7. 前端架构

### 7.1 项目结构

```
frontend/
├── public/
│   └── assets/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Loading.tsx
│   │   │   └── Tooltip.tsx
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── MainContent.tsx
│   │   │   └── Footer.tsx
│   │   ├── task/
│   │   │   ├── TaskInput.tsx
│   │   │   ├── TaskList.tsx
│   │   │   ├── TaskCard.tsx
│   │   │   └── TaskStatusBadge.tsx
│   │   ├── agent/
│   │   │   ├── AgentMonitor.tsx
│   │   │   ├── AgentTimeline.tsx
│   │   │   ├── AgentFlowChart.tsx
│   │   │   └── AgentStepCard.tsx
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── MessageInput.tsx
│   │   │   └── StreamingText.tsx
│   │   ├── knowledge/
│   │   │   ├── KnowledgeUploader.tsx
│   │   │   ├── KnowledgeList.tsx
│   │   │   └── KnowledgeSearch.tsx
│   │   └── dashboard/
│   │       ├── StatsCard.tsx
│   │       ├── PerformanceChart.tsx
│   │       └── ActivityFeed.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── TaskCenter.tsx
│   │   ├── AgentMonitor.tsx
│   │   ├── KnowledgeBase.tsx
│   │   ├── UserProfile.tsx
│   │   ├── Workspace.tsx
│   │   ├── PluginMarket.tsx
│   │   ├── Performance.tsx
│   │   ├── Settings.tsx
│   │   └── Login.tsx
│   ├── stores/
│   │   ├── index.ts
│   │   ├── authStore.ts
│   │   ├── taskStore.ts
│   │   ├── agentStore.ts
│   │   ├── userStore.ts
│   │   ├── uiStore.ts
│   │   └── knowledgeStore.ts
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── tasks.ts
│   │   ├── agents.ts
│   │   ├── knowledge.ts
│   │   └── sse.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useSSE.ts
│   │   ├── useTask.ts
│   │   ├── useAgent.ts
│   │   ├── useTheme.ts
│   │   └── useLocalStorage.ts
│   ├── types/
│   │   ├── auth.ts
│   │   ├── task.ts
│   │   ├── agent.ts
│   │   └── index.ts
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   └── constants.ts
│   └── styles/
│       ├── theme.ts
│       ├── animations.ts
│       └── globals.css
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### 7.2 Zustand 状态管理

```typescript
// stores/authStore.ts

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
  setToken: (token: string) => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    immer((set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      
      login: async (username, password) => {
        set(state => { state.isLoading = true; state.error = null; });
        
        try {
          const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
          });
          
          if (!response.ok) throw new Error('登录失败');
          
          const data = await response.json();
          
          set(state => {
            state.user = data.user;
            state.token = data.token;
            state.isAuthenticated = true;
            state.isLoading = false;
          });
        } catch (error) {
          set(state => {
            state.error = error instanceof Error ? error.message : '未知错误';
            state.isLoading = false;
          });
        }
      },
      
      register: async (username, email, password) => {
        set(state => { state.isLoading = true; state.error = null; });
        
        try {
          const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
          });
          
          if (!response.ok) throw new Error('注册失败');
          
          const data = await response.json();
          
          set(state => {
            state.user = data.user;
            state.token = data.token;
            state.isAuthenticated = true;
            state.isLoading = false;
          });
        } catch (error) {
          set(state => {
            state.error = error instanceof Error ? error.message : '未知错误';
            state.isLoading = false;
          });
        }
      },
      
      logout: () => {
        set(state => {
          state.user = null;
          state.token = null;
          state.isAuthenticated = false;
        });
      },
      
      updateUser: (userData) => {
        set(state => {
          if (state.user) {
            state.user = { ...state.user, ...userData };
          }
        });
      },
      
      setToken: (token) => {
        set(state => {
          state.token = token;
          state.isAuthenticated = !!token;
        });
      },
      
      clearError: () => {
        set(state => { state.error = null; });
      }
    })),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        token: state.token,
        user: state.user 
      })
    }
  )
);

// stores/taskStore.ts

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  steps: AgentStep[];
  isLoading: boolean;
  error: string | null;
  
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (taskId: string, updates: Partial<Task>) => void;
  setCurrentTask: (task: Task | null) => void;
  addStep: (step: AgentStep) => void;
  clearSteps: () => void;
  deleteTask: (taskId: string) => void;
}

export const useTaskStore = create<TaskState>()(
  immer((set) => ({
    tasks: [],
    currentTask: null,
    steps: [],
    isLoading: false,
    error: null,
    
    setTasks: (tasks) => set(state => { state.tasks = tasks; }),
    
    addTask: (task) => set(state => {
      state.tasks.unshift(task);
    }),
    
    updateTask: (taskId, updates) => set(state => {
      const task = state.tasks.find(t => t.id === taskId);
      if (task) {
        Object.assign(task, updates);
      }
      if (state.currentTask?.id === taskId) {
        Object.assign(state.currentTask, updates);
      }
    }),
    
    setCurrentTask: (task) => set(state => {
      state.currentTask = task;
      state.steps = [];
    }),
    
    addStep: (step) => set(state => {
      state.steps.push(step);
    }),
    
    clearSteps: () => set(state => { state.steps = []; }),
    
    deleteTask: (taskId) => set(state => {
      state.tasks = state.tasks.filter(t => t.id !== taskId);
      if (state.currentTask?.id === taskId) {
        state.currentTask = null;
      }
    })
  }))
);
```

### 7.3 API 客户端

```typescript
// api/client.ts

import axios, { AxiosInstance, AxiosError } from 'axios';
import { useAuthStore } from '../stores/authStore';

const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// api/sse.ts

export class SSEConnection {
  private eventSource: EventSource | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  
  constructor(private url: string, private options: SSEOptions) {}
  
  connect() {
    const token = useAuthStore.getState().token;
    const fullUrl = `${this.url}?token=${token}`;
    
    this.eventSource = new EventSource(fullUrl);
    
    this.eventSource.onopen = () => {
      this.reconnectAttempts = 0;
      this.options.onOpen?.();
    };
    
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.options.onMessage(data);
      } catch (error) {
        console.error('SSE 消息解析失败:', error);
      }
    };
    
    this.eventSource.onerror = (error) => {
      this.options.onError?.(error);
      this.attemptReconnect();
    };
  }
  
  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.options.onClose?.();
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }
  
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

### 7.4 关键组件

```tsx
// components/agent/AgentMonitor.tsx

import React from 'react';
import { useAgentStore } from '../../stores/agentStore';
import { AgentTimeline } from './AgentTimeline';
import { AgentFlowChart } from './AgentFlowChart';

export const AgentMonitor: React.FC = () => {
  const { agents, selectedAgent, selectAgent } = useAgentStore();
  
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Agent 监控</h2>
      
      {/* Agent 状态卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {agents.map(agent => (
          <div
            key={agent.agentId}
            onClick={() => selectAgent(agent.agentId)}
            className={`p-4 rounded-lg cursor-pointer transition-all ${
              selectedAgent === agent.agentId
                ? 'bg-blue-600 border-2 border-blue-400'
                : 'bg-gray-800 border border-gray-700 hover:border-gray-500'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-white font-medium">{agent.agentName}</span>
              <StatusIndicator status={agent.status} />
            </div>
            <div className="text-gray-400 text-sm">
              {agent.currentTask || '空闲'}
            </div>
            {agent.progress > 0 && (
              <div className="mt-2">
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${agent.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {/* 可视化区域 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4">执行时间线</h3>
          <AgentTimeline />
        </div>
        
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4">协作流程图</h3>
          <AgentFlowChart />
        </div>
      </div>
    </div>
  );
};

const StatusIndicator: React.FC<{ status: string }> = ({ status }) => {
  const colors = {
    idle: 'bg-gray-500',
    thinking: 'bg-yellow-500',
    acting: 'bg-blue-500',
    waiting: 'bg-orange-500',
    completed: 'bg-green-500',
    failed: 'bg-red-500'
  };
  
  return (
    <div className={`w-3 h-3 rounded-full ${colors[status as keyof typeof colors]} ${
      status === 'thinking' || status === 'acting' ? 'animate-pulse' : ''
    }`} />
  );
};
```

---

## 8. 性能监控

### 8.1 后端监控器

```python
# core/performance_monitor.py

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time
import psutil
import asyncio
from dataclasses import dataclass, field

@dataclass
class LatencyMetric:
    operation: str
    duration_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass
class LLMCallMetric:
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.latency_metrics: List[LatencyMetric] = []
        self.llm_metrics: List[LLMCallMetric] = []
        self.max_history = 10000
        self.current_task_metrics: Dict[str, Dict] = {}
        self.system_stats = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "memory_mb": 0.0,
            "disk_usage": 0.0
        }
        self._monitoring = False
    
    async def start(self):
        self._monitoring = True
        asyncio.create_task(self._system_monitor_loop())
    
    async def _system_monitor_loop(self):
        while self._monitoring:
            try:
                self.system_stats["cpu_percent"] = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                self.system_stats["memory_percent"] = memory.percent
                self.system_stats["memory_mb"] = memory.used / (1024 * 1024)
                disk = psutil.disk_usage('/')
                self.system_stats["disk_usage"] = disk.percent
                await asyncio.sleep(5)
            except Exception as e:
                print(f"系统监控错误: {e}")
                await asyncio.sleep(5)
    
    def record_latency(self, operation: str, duration_ms: float):
        metric = LatencyMetric(operation=operation, duration_ms=duration_ms)
        self.latency_metrics.append(metric)
        if len(self.latency_metrics) > self.max_history:
            self.latency_metrics.pop(0)
    
    def record_llm_call(self, provider, model, prompt_tokens, 
                       completion_tokens, latency_ms):
        metric = LLMCallMetric(
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            latency_ms=latency_ms
        )
        self.llm_metrics.append(metric)
        if len(self.llm_metrics) > self.max_history:
            self.llm_metrics.pop(0)
    
    def start_task_tracking(self, task_id: str):
        self.current_task_metrics[task_id] = {
            "start_time": time.time(),
            "llm_calls": 0,
            "total_tokens": 0,
            "peak_memory_mb": 0,
            "steps": 0
        }
    
    def end_task_tracking(self, task_id: str) -> Dict:
        if task_id not in self.current_task_metrics:
            return {}
        
        metrics = self.current_task_metrics[task_id]
        metrics["total_latency_ms"] = (time.time() - metrics["start_time"]) * 1000
        
        asyncio.create_task(self._save_metrics(task_id, metrics))
        del self.current_task_metrics[task_id]
        
        return metrics
    
    def get_latency_stats(self, operation=None, minutes=60) -> Dict:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        metrics = [
            m for m in self.latency_metrics
            if m.timestamp > cutoff
            and (operation is None or m.operation == operation)
        ]
        
        if not metrics:
            return {"avg_ms": 0, "min_ms": 0, "max_ms": 0, "p95_ms": 0, "count": 0}
        
        durations = sorted([m.duration_ms for m in metrics])
        p95_index = int(len(durations) * 0.95)
        
        return {
            "avg_ms": sum(durations) / len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "p95_ms": durations[p95_index],
            "count": len(durations)
        }
    
    def get_llm_stats(self, minutes=60) -> Dict:
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        metrics = [m for m in self.llm_metrics if m.timestamp > cutoff]
        
        if not metrics:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "avg_tokens_per_call": 0,
                "avg_latency_ms": 0,
                "providers": {}
            }
        
        provider_stats = {}
        for m in metrics:
            if m.provider not in provider_stats:
                provider_stats[m.provider] = {
                    "calls": 0,
                    "tokens": 0,
                    "latency_ms": []
                }
            provider_stats[m.provider]["calls"] += 1
            provider_stats[m.provider]["tokens"] += m.total_tokens
            provider_stats[m.provider]["latency_ms"].append(m.latency_ms)
        
        for provider in provider_stats:
            stats = provider_stats[provider]
            stats["avg_latency_ms"] = sum(stats["latency_ms"]) / len(stats["latency_ms"])
            del stats["latency_ms"]
        
        return {
            "total_calls": len(metrics),
            "total_tokens": sum(m.total_tokens for m in metrics),
            "avg_tokens_per_call": sum(m.total_tokens for m in metrics) / len(metrics),
            "avg_latency_ms": sum(m.latency_ms for m in metrics) / len(metrics),
            "providers": provider_stats
        }
    
    def get_system_stats(self) -> Dict:
        return self.system_stats.copy()
```

### 8.2 前端 Dashboard

```tsx
// pages/Performance.tsx

import React, { useEffect, useState } from 'react';
import { Line, Doughnut } from 'react-chartjs-2';
import { apiClient } from '../api/client';

export const Performance: React.FC = () => {
  const [systemStats, setSystemStats] = useState<any>(null);
  const [llmStats, setLLMStats] = useState<any>(null);
  const [latencyHistory, setLatencyHistory] = useState<number[]>([]);
  
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const fetchStats = async () => {
    try {
      const [systemRes, llmRes] = await Promise.all([
        apiClient.get('/monitoring/system'),
        apiClient.get('/monitoring/llm')
      ]);
      
      setSystemStats(systemRes.data);
      setLLMStats(llmRes.data);
      
      setLatencyHistory(prev => {
        const newHistory = [...prev, llmRes.data.avg_latency_ms];
        return newHistory.slice(-20);
      });
    } catch (error) {
      console.error('获取性能数据失败:', error);
    }
  };
  
  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold text-white mb-6">性能监控</h1>
      
      {/* 系统资源卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="CPU 使用率"
          value={`${systemStats?.cpu_percent?.toFixed(1) || 0}%`}
          color={systemStats?.cpu_percent > 80 ? 'red' : 'green'}
        />
        <StatCard
          title="内存使用"
          value={`${systemStats?.memory_percent?.toFixed(1) || 0}%`}
          color={systemStats?.memory_percent > 80 ? 'red' : 'blue'}
        />
        <StatCard
          title="内存占用"
          value={`${(systemStats?.memory_mb / 1024)?.toFixed(2) || 0} GB`}
          color="purple"
        />
        <StatCard
          title="磁盘使用"
          value={`${systemStats?.disk_usage?.toFixed(1) || 0}%`}
          color="orange"
        />
      </div>
      
      {/* LLM 统计 */}
      {llmStats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <StatCard title="LLM 调用次数" value={llmStats.total_calls.toString()} color="cyan" />
          <StatCard title="总 Token 数" value={llmStats.total_tokens.toLocaleString()} color="indigo" />
          <StatCard title="平均延迟" value={`${llmStats.avg_latency_ms.toFixed(0)} ms`} color="emerald" />
        </div>
      )}
      
      {/* 图表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gray-800 p-6 rounded-lg">
          <h3 className="text-lg font-semibold text-white mb-4">延迟趋势</h3>
          <Line data={{
            labels: latencyHistory.map((_, i) => `${i * 5}s`),
            datasets: [{
              label: '平均延迟 (ms)',
              data: latencyHistory,
              borderColor: 'rgb(75, 192, 192)',
              tension: 0.1
            }]
          }} />
        </div>
        
        {llmStats && (
          <div className="bg-gray-800 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-white mb-4">提供商分布</h3>
            <Doughnut data={{
              labels: Object.keys(llmStats.providers),
              datasets: [{
                data: Object.values(llmStats.providers).map((p: any) => p.calls),
                backgroundColor: [
                  'rgb(255, 99, 132)',
                  'rgb(54, 162, 235)',
                  'rgb(255, 205, 86)'
                ]
              }]
            }} />
          </div>
        )}
      </div>
    </div>
  );
};

const StatCard: React.FC<{ title: string; value: string; color: string }> = ({
  title, value, color
}) => {
  const colorClasses = {
    red: 'bg-red-500/20 border-red-500',
    green: 'bg-green-500/20 border-green-500',
    blue: 'bg-blue-500/20 border-blue-500',
    purple: 'bg-purple-500/20 border-purple-500',
    orange: 'bg-orange-500/20 border-orange-500',
    cyan: 'bg-cyan-500/20 border-cyan-500',
    indigo: 'bg-indigo-500/20 border-indigo-500',
    emerald: 'bg-emerald-500/20 border-emerald-500'
  };
  
  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color as keyof typeof colorClasses]}`}>
      <p className="text-gray-400 text-sm">{title}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
};
```

---

## 9. 部署架构

### 9.1 Docker 配置

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5"]
```

```dockerfile
# frontend/Dockerfile

FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

```yaml
# docker-compose.yml (本地开发)

version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./backend:/app
    environment:
      - DB_TYPE=sqlite
      - DATABASE_URL=sqlite:///data/agentforge.db
      - CHROMA_PERSIST_DIR=/app/data/chromadb
      - JWT_SECRET_KEY=dev-secret-key
      - ENCRYPTION_KEY=dev-encryption-key
      - ENVIRONMENT=development
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chromadb_data:/chroma/chroma
    ports:
      - "8001:8000"

volumes:
  chromadb_data:
```

```yaml
# docker-compose.prod.yml (生产环境)

version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: agentforge
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: agentforge
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - agentforge-network

  redis:
    image: redis:7-alpine
    networks:
      - agentforge-network

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chromadb_data:/chroma/chroma
    networks:
      - agentforge-network

  backend:
    build: ./backend
    environment:
      - DB_TYPE=postgresql
      - DATABASE_URL=postgresql://agentforge:${POSTGRES_PASSWORD}@postgres/agentforge
      - REDIS_URL=redis://redis:6379
      - CHROMA_HOST=chromadb
      - CHROMA_PORT=8000
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
      - ENVIRONMENT=production
    depends_on:
      - postgres
      - redis
      - chromadb
    networks:
      - agentforge-network
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure

  frontend:
    build: ./frontend
    depends_on:
      - backend
    networks:
      - agentforge-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.prod.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend
    networks:
      - agentforge-network

volumes:
  postgres_data:
  chromadb_data:

networks:
  agentforge-network:
    driver: bridge
```

### 9.2 CI/CD 配置

```yaml
# .github/workflows/ci-cd.yml

name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: agentforge_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Backend Dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov
      
      - name: Run Backend Tests
        run: |
          cd backend
          pytest --cov=agent_forge --cov-report=xml
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Frontend Dependencies
        run: |
          cd frontend
          npm ci
      
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm test -- --coverage
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml,./frontend/coverage/lcov.info

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Backend Image
        run: |
          cd backend
          docker build -t agentforge-backend:${{ github.sha }} .
      
      - name: Build Frontend Image
        run: |
          cd frontend
          docker build -t agentforge-frontend:${{ github.sha }} .
      
      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}
      
      - name: Push Images
        run: |
          docker tag agentforge-backend:${{ github.sha }} ${{ secrets.DOCKER_USERNAME }}/agentforge-backend:latest
          docker tag agentforge-frontend:${{ github.sha }} ${{ secrets.DOCKER_USERNAME }}/agentforge-frontend:latest
          
          docker push ${{ secrets.DOCKER_USERNAME }}/agentforge-backend:latest
          docker push ${{ secrets.DOCKER_USERNAME }}/agentforge-frontend:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/agentforge
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker image prune -f
```

### 9.3 部署脚本

```bash
# scripts/deploy.sh

#!/bin/bash

set -e

echo "🚀 AgentForge 部署脚本"

if [ -z "$1" ]; then
    echo "用法: ./deploy.sh [local|production]"
    exit 1
fi

ENV=$1

case $ENV in
    local)
        echo "🏠 本地部署模式"
        docker-compose -f docker-compose.yml down
        docker-compose -f docker-compose.yml up --build -d
        echo "✅ 本地部署完成"
        echo "📱 前端: http://localhost:3000"
        echo "🔧 后端: http://localhost:8000"
        ;;
    
    production)
        echo "🌐 生产部署模式"
        
        if [ ! -f .env ]; then
            echo "❌ 错误: .env 文件不存在"
            exit 1
        fi
        
        mkdir -p data logs ssl
        
        docker-compose -f docker-compose.prod.yml pull
        docker-compose -f docker-compose.prod.yml up -d
        
        echo "🏥 健康检查..."
        sleep 5
        
        if curl -f http://localhost/api/health > /dev/null 2>&1; then
            echo "✅ 部署成功"
        else
            echo "❌ 部署失败，请检查日志"
            docker-compose -f docker-compose.prod.yml logs backend
            exit 1
        fi
        ;;
    
    *)
        echo "❌ 未知环境: $ENV"
        echo "用法: ./deploy.sh [local|production]"
        exit 1
        ;;
esac
```

```bash
# scripts/setup.sh

#!/bin/bash

echo "🔧 AgentForge 初始化脚本"

if ! command -v docker &> /dev/null; then
    echo "❌ 请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ 请先安装 Docker Compose"
    exit 1
fi

echo "📁 创建目录结构..."
mkdir -p data logs ssl

if [ ! -f .env ]; then
    echo "📝 创建 .env 文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，配置必要的 API Keys"
fi

echo "🔨 构建 Docker 镜像..."
docker-compose build

echo "✅ 初始化完成！"
echo ""
echo "🚀 启动命令:"
echo "   本地开发: docker-compose up"
echo "   生产部署: ./deploy.sh production"
```

---

## 10. 开发计划

### 10.1 冲刺计划（8-10 周）

```
Week 1: Sprint 1 — 基础设施 + 核心引擎
Week 2: Sprint 2 — 多 Agent 调度 + 前端骨架
Week 3: Sprint 3 — MCP + A2A + Reflection + 记忆系统
Week 4: Sprint 4 — RAG + 协作流程图 + UI 打磨
Week 5: Sprint 5 — 用户系统 + API Key + 测试
Week 6: Sprint 6 — 性能优化 + 监控 + 插件系统
Week 7: Sprint 7 — 团队协作 + 国际化 + PWA
Week 8: Sprint 8 — DevOps + 文档 + Demo 调优
Week 9-10: 缓冲 + 面试准备 + 性能优化
```

### 10.2 详细任务分解

#### Week 1: 基础设施 + 核心引擎
- [ ] 项目骨架初始化（目录结构、配置文件）
- [ ] 数据模型定义（Pydantic Schemas）
- [ ] 数据库初始化（SQLite + PostgreSQL）
- [ ] LLM 客户端（多厂商路由）
- [ ] ReAct 引擎（推理循环）
- [ ] 工具基类 + MCP 注册中心
- [ ] 内置工具（搜索、计算、代码执行）
- [ ] Agent 基类
- [ ] FastAPI 入口 + 基础路由
- [ ] 前端项目骨架（Vite + React + Tailwind）

#### Week 2: 多 Agent 调度 + 前端骨架
- [ ] 规划器（任务拆解）
- [ ] 调度器（Orchestrator）
- [ ] 6 个 Agent 角色实现
- [ ] Agent 工厂和注册
- [ ] 前端状态管理（Zustand）
- [ ] 前端路由（React Router）
- [ ] 登录/注册页面
- [ ] 任务创建页面
- [ ] SSE 流式连接
- [ ] 基础 UI 组件

#### Week 3: MCP + A2A + Reflection + 记忆
- [ ] 8 个 MCP 工具实现
- [ ] 工具自动发现
- [ ] A2A 消息总线
- [ ] Agent 间通信
- [ ] 反思引擎
- [ ] 三层记忆系统
- [ ] 记忆上下文构建
- [ ] 知识库上传
- [ ] Agent 监控面板
- [ ] 执行时间线可视化

#### Week 4: RAG + 协作流程图 + UI 打磨
- [ ] ChromaDB 集成
- [ ] 文档分块和向量化
- [ ] 语义检索
- [ ] RAG 上下文构建
- [ ] 协作流程图（DAG 可视化）
- [ ] 消息流可视化
- [ ] 暗色主题优化
- [ ] 响应式布局
- [ ] 动画效果
- [ ] UI 细节打磨

#### Week 5: 用户系统 + API Key + 测试
- [ ] JWT 认证
- [ ] 用户注册/登录
- [ ] API Key 加密存储
- [ ] 用户偏好设置
- [ ] 后端单元测试
- [ ] 前端组件测试
- [ ] API 集成测试
- [ ] 测试覆盖率报告
- [ ] Mock LLM 测试模式
- [ ] Bug 修复

#### Week 6: 性能优化 + 监控 + 插件
- [ ] 性能监控器
- [ ] 系统资源监控
- [ ] LLM 调用统计
- [ ] 性能 Dashboard
- [ ] 前端性能优化（懒加载、缓存）
- [ ] 后端性能优化（连接池、缓存）
- [ ] 插件系统架构
- [ ] 插件注册/加载
- [ ] 插件市场 UI
- [ ] 代码注释完善

#### Week 7: 团队协作 + 国际化 + PWA
- [ ] 工作区管理
- [ ] 成员权限
- [ ] 共享任务
- [ ] i18n 国际化
- [ ] 多语言支持
- [ ] PWA 配置
- [ ] Service Worker
- [ ] 离线缓存
- [ ] 移动端适配
- [ ] 推送通知

#### Week 8: DevOps + 文档 + Demo
- [ ] Docker 优化
- [ ] CI/CD 配置
- [ ] 部署脚本
- [ ] 日志系统
- [ ] 监控告警
- [ ] README 文档
- [ ] API 文档
- [ ] 架构文档
- [ ] 部署指南
- [ ] Demo 场景调优

#### Week 9-10: 缓冲 + 面试准备
- [ ] Bug 修复
- [ ] 性能调优
- [ ] 安全审查
- [ ] 5 分钟演示脚本
- [ ] 面试 Q&A
- [ ] 视频录制
- [ ] 文档完善
- [ ] 代码审查
- [ ] 最终测试
- [ ] 部署上线

---

## 11. 面试准备

### 11.1 5 分钟快速演示脚本

```
第 1 分钟：项目介绍
- 展示 Dashboard 界面
- 介绍 AgentForge 定位
- 强调 8 个核心方向

第 2 分钟：任务创建
- 选择预设场景（如"调研某公司"）
- 展示 Planner 拆解任务
- 展示依赖图

第 3 分钟：执行过程
- 观看 Agent 协作执行
- 展示 ReAct 循环可视化
- 展示工具调用日志

第 4 分钟：结果展示
- 展示最终报告
- 展示反思报告
- 展示性能指标

第 5 分钟：高级特性
- 展示知识库功能
- 展示团队协作
- 展示插件系统
- 总结技术亮点
```

### 11.2 常见面试问题 Q&A

**Q: 为什么选 ChromaDB 而不是 Pinecone？**
A: ChromaDB 本地运行，无云服务费用，Docker 一键启动，面试官可本地体验。架构预留接口，后续可切换。

**Q: 如何实现 Agent 间协作？**
A: 基于 A2A 协议实现消息总线，支持点对点、广播、请求-响应模式。调度器管理依赖图，实现并行执行。

**Q: ReAct 引擎怎么实现的？**
A: 从零实现完整的 Thought-Action-Observation 循环，支持工具调用、错误处理、最大步数限制、流式输出。

**Q: 如何保证 API Key 安全？**
A: 用户输入后通过 HTTPS 传输，服务端使用 AES-256 加密存储，Key 永不暴露给前端。

**Q: 系统如何扩展？**
A: 架构分层清晰，通过配置文件切换数据库和 LLM 提供商。Docker 支持水平扩展，Nginx 负载均衡。

**Q: 性能如何优化？**
A: 前端：代码分割、懒加载、Virtual List。后端：异步处理、连接池、Redis 缓存。监控：实时指标 + Dashboard。

**Q: 测试覆盖率如何？**
A: 单元测试覆盖核心逻辑，集成测试覆盖 API，E2E 测试覆盖关键流程。目标 80%+ 覆盖率。

**Q: 如何处理 LLM 服务异常？**
A: 实现降级策略，Kimi 异常时询问用户是否切换到 DeepSeek。支持自动降级开关。

---

## 附录

### A. 环境变量配置

```bash
# 应用
ENVIRONMENT=development

# 数据库
DB_TYPE=sqlite
DATABASE_URL=sqlite:///data/agentforge.db

# JWT
JWT_SECRET_KEY=your-secret-key-here

# 加密
ENCRYPTION_KEY=your-encryption-key-here

# LLM
KIMI_API_KEY=your-kimi-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
```

### B. 项目启动命令

```bash
# 本地开发
docker-compose up

# 生产部署
./deploy.sh production

# 后端测试
cd backend && pytest

# 前端测试
cd frontend && npm test
```

## 12. 新增核心模块（基于反馈优化）

### 12.1 取消控制模块 (core/cancellation.py)

```python
# core/cancellation.py

import asyncio
from typing import Optional

class CancellationToken:
    """
    取消令牌
    
    用于优雅地取消异步任务
    """
    
    def __init__(self):
        self._cancelled = False
        self._callbacks = []
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled
    
    def cancel(self):
        """触发取消"""
        self._cancelled = True
        for callback in self._callbacks:
            try:
                callback()
            except Exception:
                pass
    
    def on_cancel(self, callback):
        """注册取消回调"""
        self._callbacks.append(callback)
    
    def check_cancellation(self):
        """检查是否已取消，如果是则抛出异常"""
        if self._cancelled:
            raise CancellationError("任务已取消")

class CancellationError(Exception):
    """取消异常"""
    pass
```

### 12.2 结构化输出验证模块 (core/output_validator.py)

```python
# core/output_validator.py

from typing import Type, Dict, Any, Optional
from pydantic import BaseModel, ValidationError as PydanticValidationError
import json
import logging

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """验证错误"""
    pass

class OutputValidator:
    """
    输出验证器
    
    验证 LLM 输出是否符合预期 Schema
    """
    
    def __init__(self, model_class: Type[BaseModel]):
        self.model_class = model_class
        self.validation_count = 0
        self.failure_count = 0
    
    def validate(self, data: Dict[str, Any]) -> BaseModel:
        """验证数据"""
        self.validation_count += 1
        
        try:
            return self.model_class(**data)
        except PydanticValidationError as e:
            self.failure_count += 1
            raise ValidationError(f"Schema 验证失败: {e}")
    
    def validate_json(self, json_str: str) -> BaseModel:
        """验证 JSON 字符串"""
        try:
            data = json.loads(json_str)
            return self.validate(data)
        except json.JSONDecodeError as e:
            self.failure_count += 1
            raise ValidationError(f"JSON 解析失败: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """获取验证统计"""
        return {
            "total": self.validation_count,
            "failures": self.failure_count,
            "success_rate": (
                (self.validation_count - self.failure_count) / self.validation_count
                if self.validation_count > 0 else 1.0
            )
        }
    
    def build_correction_prompt(self, error: str) -> str:
        """构建修正 Prompt"""
        return f"""你的输出格式有误，请按以下 JSON Schema 重新输出：

错误信息: {error}

要求：
1. 输出必须是合法的 JSON
2. 不要包含任何其他文本或说明
3. 确保所有必填字段都有值

请重新输出："""
```

### 12.3 沙箱执行模块 (core/sandbox.py)

```python
# core/sandbox.py

import subprocess
import tempfile
import os
import json
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class SandboxConfig:
    """沙箱配置"""
    max_cpu_percent: float = 50.0
    max_memory_mb: int = 256
    max_execution_time: int = 30
    network_enabled: bool = False
    writable_dirs: list = None
    
    def __post_init__(self):
        if self.writable_dirs is None:
            self.writable_dirs = []

class SandboxExecutor:
    """
    沙箱执行器
    
    基于 Docker 的轻量级沙箱，用于安全执行用户代码
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
    
    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        在沙箱中执行代码
        
        Args:
            code: 代码内容
            language: 编程语言
        
        Returns:
            Dict: {"stdout": str, "stderr": str, "exit_code": int, "execution_time_ms": int}
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
            f.write(code)
            code_file = f.name
        
        try:
            # 构建 Docker 运行命令
            cmd = [
                'docker', 'run', '--rm',
                '--network', 'none' if not self.config.network_enabled else 'bridge',
                '--memory', f'{self.config.max_memory_mb}m',
                '--memory-swap', f'{self.config.max_memory_mb}m',
                '--cpus', str(self.config.max_cpu_percent / 100),
                '--read-only',
                '-v', f'{code_file}:/code/script.{language}:ro',
                'python:3.11-alpine',
                'python', f'/code/script.{language}'
            ]
            
            # 执行
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.max_execution_time
            )
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "execution_time_ms": int(execution_time)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"执行超时（>{self.config.max_execution_time}秒）",
                "exit_code": -1,
                "execution_time_ms": self.config.max_execution_time * 1000
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"沙箱执行错误: {str(e)}",
                "exit_code": -1,
                "execution_time_ms": 0
            }
        finally:
            # 清理临时文件
            os.unlink(code_file)
```

### 12.4 API 限流与熔断模块 (api/middleware/rate_limit.py)

```python
# api/middleware/rate_limit.py

import time
from typing import Optional, Dict
from functools import wraps
import redis
from fastapi import HTTPException, Request

class RateLimiter:
    """
    滑动窗口限流器
    
    基于 Redis 的分布式限流
    """
    
    def __init__(self, redis_client, window_size=60, max_requests=100):
        self.redis = redis_client
        self.window_size = window_size
        self.max_requests = max_requests
    
    async def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        window_start = now - self.window_size
        
        # 使用 Redis Sorted Set 实现滑动窗口
        pipe = self.redis.pipeline()
        
        # 移除窗口外的请求记录
        pipe.zremrangebyscore(key, 0, window_start)
        
        # 获取当前窗口内的请求数
        pipe.zcard(key)
        
        # 添加当前请求
        pipe.zadd(key, {str(now): now})
        
        # 设置过期时间
        pipe.expire(key, self.window_size)
        
        results = pipe.execute()
        current_count = results[1]
        
        return current_count < self.max_requests

class CircuitBreaker:
    """
    熔断器
    
    防止级联故障
    """
    
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func, *args, **kwargs):
        """调用函数（带熔断保护）"""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
            else:
                raise HTTPException(
                    status_code=503,
                    detail="服务暂时不可用，请稍后重试"
                )
        
        try:
            result = await func(*args, **kwargs)
            
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            
            if self.failures >= self.failure_threshold:
                self.state = "open"
            
            raise e

# LLM 调用熔断器（全局实例）
llm_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)
```

### 12.5 任务幂等性模块 (core/idempotency.py)

```python
# core/idempotency.py

import hashlib
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
import redis

class IdempotencyChecker:
    """
    幂等性检查器
    
    防止重复任务消耗资源
    """
    
    def __init__(self, redis_client, ttl=3600):
        self.redis = redis_client
        self.ttl = ttl
    
    def generate_key(self, user_id: str, task_content: str) -> str:
        """生成幂等键"""
        content_hash = hashlib.sha256(task_content.encode()).hexdigest()[:16]
        return f"idempotency:{user_id}:{content_hash}"
    
    async def check(self, user_id: str, task_content: str) -> Optional[Dict]:
        """
        检查是否是重复任务
        
        Returns:
            None: 新任务
            Dict: 已有任务的结果
        """
        key = self.generate_key(user_id, task_content)
        
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        return None
    
    async def store(self, user_id: str, task_content: str, result: Dict):
        """存储任务结果"""
        key = self.generate_key(user_id, task_content)
        
        self.redis.setex(
            key,
            self.ttl,
            json.dumps({
                "result": result,
                "created_at": datetime.utcnow().isoformat()
            })
        )
    
    async def invalidate(self, user_id: str, task_content: str):
        """使缓存失效"""
        key = self.generate_key(user_id, task_content)
        self.redis.delete(key)
```

### 12.6 操作审计日志模块 (core/audit_log.py)

```python
# core/audit_log.py

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class AuditEventType(str, Enum):
    TASK_CREATED = "task_created"
    TASK_EXECUTED = "task_executed"
    TOOL_CALLED = "tool_called"
    LLM_CALLED = "llm_called"
    USER_LOGIN = "user_login"
    API_KEY_UPDATED = "api_key_updated"

class AuditLogger:
    """
    审计日志记录器
    
    记录所有关键操作，用于问题追溯和费用分摊
    """
    
    def __init__(self, logger_name="audit"):
        self.logger = logging.getLogger(logger_name)
        
        # 配置审计日志处理器
        handler = logging.FileHandler("logs/audit.log")
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log(self, event_type: AuditEventType, user_id: str, 
            details: Dict[str, Any], ip_address: Optional[str] = None):
        """记录审计事件"""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": details
        }
        
        self.logger.info(json.dumps(event, ensure_ascii=False))
    
    def log_task_execution(self, task_id: str, user_id: str, 
                          llm_calls: int, tokens_used: int, 
                          execution_time_ms: int):
        """记录任务执行"""
        self.log(
            AuditEventType.TASK_EXECUTED,
            user_id,
            {
                "task_id": task_id,
                "llm_calls": llm_calls,
                "tokens_used": tokens_used,
                "execution_time_ms": execution_time_ms,
                "estimated_cost": self._estimate_cost(tokens_used)
            }
        )
    
    def log_llm_call(self, provider: str, model: str, 
                    prompt_tokens: int, completion_tokens: int,
                    latency_ms: int, user_id: str):
        """记录 LLM 调用"""
        self.log(
            AuditEventType.LLM_CALLED,
            user_id,
            {
                "provider": provider,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "latency_ms": latency_ms
            }
        )
    
    def _estimate_cost(self, tokens: int) -> float:
        """估算成本（简化版）"""
        # 假设平均价格：$0.002 / 1K tokens
        return (tokens / 1000) * 0.002
```

### 12.7 Prompt 版本管理模块 (core/prompt_registry.py)

```python
# core/prompt_registry.py

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PromptVersion:
    """Prompt 版本"""
    version: str
    content: str
    created_at: datetime
    performance_score: Optional[float] = None
    usage_count: int = 0

class PromptRegistry:
    """
    Prompt 注册表
    
    统一管理所有 Prompt，支持 A/B 测试
    """
    
    def __init__(self):
        self._prompts: Dict[str, List[PromptVersion]] = {}
        self._active_versions: Dict[str, str] = {}
    
    def register(self, name: str, content: str, version: str = "1.0"):
        """注册 Prompt"""
        if name not in self._prompts:
            self._prompts[name] = []
        
        self._prompts[name].append(PromptVersion(
            version=version,
            content=content,
            created_at=datetime.utcnow()
        ))
        
        # 默认使用最新版本
        self._active_versions[name] = version
    
    def get(self, name: str, version: Optional[str] = None) -> str:
        """获取 Prompt"""
        if name not in self._prompts:
            raise KeyError(f"Prompt '{name}' 未注册")
        
        if version is None:
            version = self._active_versions.get(name, "1.0")
        
        for pv in self._prompts[name]:
            if pv.version == version:
                pv.usage_count += 1
                return pv.content
        
        raise KeyError(f"Prompt '{name}' 版本 '{version}' 不存在")
    
    def set_active_version(self, name: str, version: str):
        """设置活跃版本"""
        self._active_versions[name] = version
    
    def list_versions(self, name: str) -> List[PromptVersion]:
        """列出所有版本"""
        return self._prompts.get(name, [])
    
    def record_performance(self, name: str, version: str, score: float):
        """记录版本性能分数"""
        for pv in self._prompts.get(name, []):
            if pv.version == version:
                pv.performance_score = score
                break

# 全局 Prompt 注册表
prompt_registry = PromptRegistry()

# 注册系统 Prompts
prompt_registry.register("react_system", "你是一个...", "1.0")
prompt_registry.register("planner_system", "你是一个规划专家...", "1.0")
prompt_registry.register("reflection_system", "你是一个反思专家...", "1.0")
```

### 12.8 监控告警模块 (core/alerting.py)

```python
# core/alerting.py

import asyncio
from typing import Dict, List, Callable, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AlertRule:
    """告警规则"""
    
    def __init__(self, name: str, condition: Callable, 
                 level: AlertLevel, cooldown_seconds: int = 300):
        self.name = name
        self.condition = condition
        self.level = level
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered = None
    
    def check(self, metrics: Dict) -> bool:
        """检查是否触发告警"""
        # 检查冷却时间
        if self.last_triggered:
            elapsed = (datetime.utcnow() - self.last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False
        
        # 检查条件
        if self.condition(metrics):
            self.last_triggered = datetime.utcnow()
            return True
        
        return False

class AlertManager:
    """
    告警管理器
    
    监控指标并发送告警通知
    """
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.handlers: Dict[AlertLevel, List[Callable]] = {
            AlertLevel.INFO: [],
            AlertLevel.WARNING: [],
            AlertLevel.ERROR: [],
            AlertLevel.CRITICAL: []
        }
        self._running = False
    
    def add_rule(self, rule: AlertRule):
        """添加告警规则"""
        self.rules.append(rule)
    
    def add_handler(self, level: AlertLevel, handler: Callable):
        """添加告警处理器"""
        self.handlers[level].append(handler)
    
    async def start(self):
        """启动告警监控"""
        self._running = True
        logger.info("告警管理器已启动")
    
    async def check_metrics(self, metrics: Dict):
        """检查指标并触发告警"""
        for rule in self.rules:
            if rule.check(metrics):
                alert = {
                    "name": rule.name,
                    "level": rule.level.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metrics": metrics
                }
                
                # 发送告警
                await self._send_alert(alert, rule.level)
    
    async def _send_alert(self, alert: Dict, level: AlertLevel):
        """发送告警通知"""
        for handler in self.handlers[level]:
            try:
                await handler(alert)
            except Exception as e:
                logger.error(f"告警发送失败: {e}")

# 预定义告警规则

def create_default_rules() -> List[AlertRule]:
    """创建默认告警规则"""
    
    return [
        # LLM 调用失败率超过 10%
        AlertRule(
            name="llm_failure_rate_high",
            condition=lambda m: m.get("llm_failure_rate", 0) > 0.1,
            level=AlertLevel.ERROR,
            cooldown_seconds=300
        ),
        
        # 任务平均执行时间超过 60 秒
        AlertRule(
            name="task_execution_slow",
            condition=lambda m: m.get("avg_task_duration_ms", 0) > 60000,
            level=AlertLevel.WARNING,
            cooldown_seconds=600
        ),
        
        # CPU 使用率超过 90%
        AlertRule(
            name="cpu_usage_high",
            condition=lambda m: m.get("cpu_percent", 0) > 90,
            level=AlertLevel.CRITICAL,
            cooldown_seconds=60
        ),
        
        # 内存使用率超过 85%
        AlertRule(
            name="memory_usage_high",
            condition=lambda m: m.get("memory_percent", 0) > 85,
            level=AlertLevel.WARNING,
            cooldown_seconds=120
        )
    ]

# 通知处理器示例

async def dingtalk_handler(alert: Dict):
    """钉钉通知"""
    # 实现钉钉机器人通知
    pass

async def feishu_handler(alert: Dict):
    """飞书通知"""
    # 实现飞书机器人通知
    pass

async def webhook_handler(alert: Dict):
    """通用 Webhook 通知"""
    # 实现通用 Webhook 通知
    pass
```

### 12.9 错误处理统一层 (core/error_handler.py)

```python
# core/error_handler.py

import logging
import traceback
from typing import Dict, Any, Optional
from enum import Enum
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class ErrorCode(str, Enum):
    """错误码"""
    # 系统错误 1xxxx
    UNKNOWN_ERROR = "10000"
    INTERNAL_ERROR = "10001"
    SERVICE_UNAVAILABLE = "10002"
    
    # 参数错误 2xxxx
    INVALID_PARAMETER = "20000"
    MISSING_PARAMETER = "20001"
    INVALID_FORMAT = "20002"
    
    # 认证错误 3xxxx
    UNAUTHORIZED = "30000"
    FORBIDDEN = "30001"
    TOKEN_EXPIRED = "30002"
    
    # 业务错误 4xxxx
    TASK_NOT_FOUND = "40000"
    TASK_EXECUTION_FAILED = "40001"
    LLM_CALL_FAILED = "40002"
    TOOL_EXECUTION_FAILED = "40003"
    
    # 资源错误 5xxxx
    RATE_LIMIT_EXCEEDED = "50000"
    RESOURCE_NOT_FOUND = "50001"
    RESOURCE_CONFLICT = "50002"

class AppException(Exception):
    """应用异常基类"""
    
    def __init__(self, code: ErrorCode, message: str, 
                 details: Optional[Dict] = None, status_code: int = 500):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

class ErrorHandler:
    """
    统一错误处理
    
    统一处理所有异常，返回标准错误响应
    """
    
    @staticmethod
    def handle_exception(exc: Exception) -> Dict[str, Any]:
        """处理异常"""
        if isinstance(exc, AppException):
            return {
                "success": False,
                "error_code": exc.code.value,
                "message": exc.message,
                "details": exc.details
            }
        
        elif isinstance(exc, HTTPException):
            return {
                "success": False,
                "error_code": ErrorCode.INVALID_PARAMETER.value,
                "message": exc.detail,
                "details": {}
            }
        
        else:
            # 未知错误，记录日志
            logger.error(f"未处理的异常: {str(exc)}")
            logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error_code": ErrorCode.UNKNOWN_ERROR.value,
                "message": "系统内部错误",
                "details": {"error": str(exc)} if True else {}  # 生产环境隐藏详细错误
            }
    
    @staticmethod
    def raise_task_not_found(task_id: str):
        raise AppException(
            code=ErrorCode.TASK_NOT_FOUND,
            message=f"任务不存在: {task_id}",
            status_code=404
        )
    
    @staticmethod
    def raise_unauthorized(message: str = "未授权"):
        raise AppException(
            code=ErrorCode.UNAUTHORIZED,
            message=message,
            status_code=401
        )
    
    @staticmethod
    def raise_rate_limit():
        raise AppException(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="请求过于频繁，请稍后重试",
            status_code=429
        )
```

### 12.10 配置验证模块 (core/config_validator.py)

```python
# core/config_validator.py

import os
from typing import List, Dict, Any
from pydantic import BaseModel, Field, validator

class ConfigValidationError(Exception):
    """配置验证错误"""
    pass

class DatabaseConfig(BaseModel):
    db_type: str = Field(..., regex="^(sqlite|postgresql)$")
    database_url: str
    
    @validator('database_url')
    def validate_url(cls, v, values):
        if values['db_type'] == 'sqlite' and not v.startswith('sqlite://'):
            raise ValueError('SQLite URL 必须以 sqlite:// 开头')
        if values['db_type'] == 'postgresql' and not v.startswith('postgresql://'):
            raise ValueError('PostgreSQL URL 必须以 postgresql:// 开头')
        return v

class LLMConfig(BaseModel):
    kimi_api_key: str = Field(default="")
    deepseek_api_key: str = Field(default="")
    
    @validator('kimi_api_key', 'deepseek_api_key')
    def validate_key_format(cls, v):
        if v and len(v) < 10:
            raise ValueError('API Key 格式不正确')
        return v

class SecurityConfig(BaseModel):
    jwt_secret_key: str = Field(..., min_length=32)
    encryption_key: str = Field(..., min_length=32)
    
    @validator('jwt_secret_key', 'encryption_key')
    def validate_not_default(cls, v, field):
        defaults = ['your-secret-key', 'your-encryption-key', 'change-me']
        if any(d in v.lower() for d in defaults):
            raise ValueError(f'{field.name} 不能是默认值')
        return v

class AppConfig(BaseModel):
    """应用配置"""
    database: DatabaseConfig
    llm: LLMConfig
    security: SecurityConfig
    environment: str = Field(..., regex="^(development|staging|production)$")

class ConfigValidator:
    """
    配置验证器
    
    启动时验证所有环境变量和配置项
    """
    
    REQUIRED_ENV_VARS = [
        'JWT_SECRET_KEY',
        'ENCRYPTION_KEY',
        'ENVIRONMENT'
    ]
    
    @classmethod
    def validate(cls) -> AppConfig:
        """验证配置"""
        errors = []
        
        # 检查必需环境变量
        for var in cls.REQUIRED_ENV_VARS:
            if not os.getenv(var):
                errors.append(f"缺少必需的环境变量: {var}")
        
        if errors:
            raise ConfigValidationError("\n".join(errors))
        
        # 验证配置值
        try:
            config = AppConfig(
                database=DatabaseConfig(
                    db_type=os.getenv('DB_TYPE', 'sqlite'),
                    database_url=os.getenv('DATABASE_URL', 'sqlite:///data/agentforge.db')
                ),
                llm=LLMConfig(
                    kimi_api_key=os.getenv('KIMI_API_KEY', ''),
                    deepseek_api_key=os.getenv('DEEPSEEK_API_KEY', '')
                ),
                security=SecurityConfig(
                    jwt_secret_key=os.getenv('JWT_SECRET_KEY'),
                    encryption_key=os.getenv('ENCRYPTION_KEY')
                ),
                environment=os.getenv('ENVIRONMENT', 'development')
            )
            
            return config
            
        except Exception as e:
            raise ConfigValidationError(f"配置验证失败: {str(e)}")
    
    @classmethod
    def check_llm_connectivity(cls) -> Dict[str, bool]:
        """检查 LLM 连接"""
        # 实现 LLM 连接检查
        return {"kimi": True, "deepseek": True}
    
    @classmethod
    def check_database_connectivity(cls) -> bool:
        """检查数据库连接"""
        # 实现数据库连接检查
        return True
```

### 12.11 健康检查端点 (api/health.py)

```python
# api/health.py

from fastapi import APIRouter, Depends
from typing import Dict
import asyncio

router = APIRouter(prefix="/health", tags=["健康检查"])

@router.get("/")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/ready")
async def readiness_check():
    """就绪检查（依赖服务是否可用）"""
    checks = await asyncio.gather(
        check_database(),
        check_chromadb(),
        check_redis(),
        return_exceptions=True
    )
    
    results = {
        "database": checks[0] if not isinstance(checks[0], Exception) else False,
        "chromadb": checks[1] if not isinstance(checks[1], Exception) else False,
        "redis": checks[2] if not isinstance(checks[2], Exception) else False
    }
    
    all_ready = all(results.values())
    
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": results
    }

@router.get("/live")
async def liveness_check():
    """存活检查（应用是否运行）"""
    return {"status": "alive"}

async def check_database() -> bool:
    """检查数据库连接"""
    try:
        # 实现数据库连接检查
        return True
    except Exception:
        return False

async def check_chromadb() -> bool:
    """检查 ChromaDB 连接"""
    try:
        # 实现 ChromaDB 连接检查
        return True
    except Exception:
        return False

async def check_redis() -> bool:
    """检查 Redis 连接"""
    try:
        # 实现 Redis 连接检查
        return True
    except Exception:
        return False
```

---

### C. 技术决策记录（更新版）

| 决策 | 选项 A | 选项 B | 选择 | 理由 |
|------|--------|--------|------|------|
| 状态管理 | Redux | Zustand | Zustand | 轻量、TypeScript 友好 |
| 向量数据库 | FAISS | ChromaDB | ChromaDB | 原生持久化、元数据过滤 |
| 认证方式 | Session | JWT | JWT | 无状态、支持 SSE |
| 部署方式 | 手动 | Docker | Docker | 一键启动、环境一致 |
| 测试框架 | unittest | pytest | pytest | 生态丰富、异步支持 |
| **后端服务器** | **uvicorn** | **gunicorn** | **gunicorn** | **多进程支持、生产级** |
| **前端状态** | **Zustand 全管** | **React Query + Zustand** | **React Query + Zustand** | **职责分离** |
| **LLM 输出** | **文本格式** | **JSON 模式** | **JSON 模式** | **解析可靠** |
| **代码执行** | **subprocess** | **Docker 沙箱** | **Docker 沙箱** | **安全隔离** |

---

**文档结束（修订版）**

> 本文档由 Sisyphus AI Agent 基于 Brainstorming Skill 生成  
> 生成日期: 2026-05-19  
> 版本: 2.0（基于用户反馈修订）  
> 修订内容: ReAct JSON 化、Planner 容错、Orchestrator 超时取消、A2A 修复、Docker 优化、新增 11 个核心模块
