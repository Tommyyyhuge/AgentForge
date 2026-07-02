# AgentForge 技术文档

## 1. 目的

本文档定义 AgentForge 重构目标版的技术架构，包括技术栈、服务边界、API 契约、Provider Adapter 模型、持久化策略和质量门禁。

本文档用于指导实现，不替代源码、迁移脚本或测试。

## 2. 固定技术栈

后端：

- Python 3.11+。
- FastAPI 与 Uvicorn。
- Pydantic v2。
- SQLAlchemy async ORM。
- Alembic migration。
- Docker/private deployment 使用 PostgreSQL 16。
- 本地开发支持 SQLite。
- Memory 向量存储使用 embedded Chroma persistent client。
- Memory fallback 使用 SQLite。
- Redis 用于缓存或消息支持。
- Provider Adapter 可使用 `httpx` 或官方 SDK。
- 认证和加密使用 `python-jose`、`passlib`、`cryptography`。

前端：

- React 19。
- TypeScript 6。
- Vite 8。
- Tailwind CSS。
- Zustand。
- React Router 7。
- React Flow。
- Recharts。
- Axios。
- Native EventSource。

基础设施：

- Docker Compose。
- Backend container。
- Frontend Nginx container。
- PostgreSQL container。
- Redis container。
- Chroma data 作为 backend storage 挂载。

## 3. 架构概览

```text
Browser
  |
  | HTTP / SSE
  v
Frontend: React + Vite + Tailwind
  |
  | /api/v1/*
  v
Backend: FastAPI
  |-- API routes
  |-- Auth middleware
  |-- Task orchestration
  |-- Planner
  |-- Agent runtime
  |-- Tool registry
  |-- Memory manager
  |-- Provider registry and adapters
  |
  | SQL
  v
PostgreSQL or SQLite

Backend
  | vector persistence
  v
Embedded Chroma

Backend
  | cache/message support
  v
Redis
```

## 4. 后端边界

目标职责：

| 区域 | 职责 |
| --- | --- |
| `api/routes` | FastAPI route、请求解析、响应组装 |
| `api/middleware` | 认证和请求级 middleware |
| `models` | Pydantic schema 和公开 API model |
| `database` | ORM model、数据库连接、migration |
| `core` | Orchestration、Planner、Execution loop、Memory、metrics、Provider 服务 |
| `agents` | 内置 Agent 实现和 factory |
| `tools` | 内置 Agent tools |
| `mcp` | Tool registry 协议和注册 |
| `utils` | 日志、加密、底层辅助函数 |

规则：

- Route handler 保持薄。
- 业务逻辑放在 `core`、`agents` 或专门 service。
- ORM model 不直接作为 API 契约返回。
- Pydantic response schema 是 API 边界。
- Provider-specific 代码不得散落在 Planner、Agent 或 route handler 中。

## 5. 前端边界

目标职责：

| 区域 | 职责 |
| --- | --- |
| `api` | HTTP/SSE client、API response parsing |
| `types` | 前端领域类型和 API 类型 |
| `stores` | Zustand state、API orchestration、必要的 optimistic state |
| `pages` | 页面级组合和 route surface |
| `components/layout` | App shell、Sidebar、Header |
| `components/ui` | 可复用 UI primitive |
| `components/charts` | Metrics 图表 |
| `components/flow` | Agent/Task flow 图 |
| `hooks` | UI 和数据流 hooks |
| `utils` | 纯 helper |

规则：

- API response normalization 放在 `api` 或 store mapping。
- Component 接收 typed props，避免直接依赖原始 backend payload。
- Page 可以组合数据流，但不重复 API mapping 逻辑。
- UI primitive 不导入 store。

## 6. API 契约

当前 API prefix 保持：

- `/api/v1`。

核心 route groups：

- `/api/v1/tasks`。
- `/api/v1/agents`。
- `/api/v1/keys`。
- `/api/v1/metrics`。
- `/api/v1/register`。
- `/api/v1/login`。
- `/api/v1/me`。

当前 route groups：

- `/api/v1/providers`。

当前 Provider routes：

- `GET /api/v1/providers/presets`：返回 Provider Registry presets。
- `GET /api/v1/providers`：返回 active ProviderConfig 列表。
- `POST /api/v1/providers`：创建 ProviderConfig。
- `GET /api/v1/providers/{provider_id}`：读取 ProviderConfig。
- `PATCH /api/v1/providers/{provider_id}`：更新 ProviderConfig。
- `DELETE /api/v1/providers/{provider_id}`：软删除 ProviderConfig。
- `POST /api/v1/providers/{provider_id}/test`：通过 Provider Adapter 返回归一化 health result。
- `GET /api/v1/providers/{provider_id}/models`：通过 Provider Adapter 获取模型列表；失败时返回 degraded 状态并允许手动录入。

Provider routes 需要登录认证，使用标准 envelope，新响应字段使用 camelCase，不返回明文 API Key。

前端 Provider API 边界：

- `frontend/src/api/providers.ts` 负责 `/api/v1/providers` 和 `/api/v1/keys` 相关 response unwrapping 与 payload mapping。
- `frontend/src/api/providers.ts` 创建 ProviderConfig 时使用调用方传入的 `providerType` 与 capability flags，不在 API client 中硬编码 Relay Provider。
- `frontend/src/stores/providerStore.ts` 负责 Provider Settings 的 API orchestration、loading/error/validation 状态、官方 preset Provider 与 Relay Provider 创建分流、Provider test result 和 model listing degraded 状态。
- Settings Provider row 使用 `/providers/{provider_id}/models` 的结果提供模型选择；model listing degraded 或没有模型时保留 manual model entry，并将当前模型传给 Provider test。
- Dashboard 复用 `providerStore` 的 ProviderConfig 和已有 health result 展示 Provider ready/degraded 状态；Dashboard 不自动触发供应商连接测试。
- Dashboard metrics 加载失败时只显示局部 error state，保留 Task、Provider 和导航入口可用。
- Dashboard Agent summary 从 `agentStore` 的 typed Agent state 派生 idle/busy/error 计数，不新增 Dashboard 专用 API payload。
- 明文 API Key 只存在于 Provider 创建请求的受控表单和提交调用中，不进入 `ProviderConfig` 领域类型或 provider store state。

### 6.1 响应 Envelope

成功：

```json
{
  "success": true,
  "data": {},
  "message": "optional message"
}
```

错误：

```json
{
  "success": false,
  "error": {
    "code": "PROVIDER_AUTH_FAILED",
    "message": "Provider authentication failed.",
    "details": {}
  }
}
```

规则：

- 新 route 必须使用标准 envelope。
- 旧 route 在不突然破坏前端的前提下逐步迁移。
- `code` 稳定且机器可读。
- `message` 对用户安全可读。
- `details` 不得包含明文 secret。

### 6.2 命名

后端 ORM 可以使用 snake_case。API JSON 需要在每个 endpoint 内保持一致。目标前端领域类型使用 camelCase。若后端返回 snake_case，前端 API/store 层必须显式映射。

新 endpoint 推荐：

- 面向前端响应使用 camelCase。
- legacy 兼容可以暂时保留 snake_case。

### 6.3 分页

目标分页响应：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "pageSize": 20,
  "totalPages": 0
}
```

### 6.4 SSE

Task stream：

- Endpoint：`/api/v1/tasks/{task_id}/stream`。
- Event types：`message`、`step`、`done`、`error`。

Agent stream：

- Endpoint：`/api/v1/agents/stream`。
- Event types：`message`、`agent_state`、`error`。

规则：

- SSE payload 必须是 JSON。
- Event 必须包含稳定对象 ID。
- 重连不得创建重复 Step。
- Task store 必须对 Task detail 返回的持久化 Step 和 SSE step update 统一按 timeline order 排序。
- Task detail Step response 必须包含稳定 `step_number`，前端将其映射为 `Step.order`。
- Task store 维护 Task stream connection state，TaskDetail 用于展示 `SSE connecting/connected/disconnected`。
- 前端组件卸载时必须关闭 EventSource。

## 7. 数据模型

当前核心实体：

- `UserORM`。
- `TaskORM`。
- `StepORM`。
- `AgentStateORM`。
- `MemoryORM`。
- `APIKeyORM`。

Provider 目标实体：

当前目标模型不创建独立 `ProviderCapability` 表。Provider 级能力保存在 `ProviderConfig.capabilities`，模型级能力保存在 `ModelConfig.supports_*` 字段。实现时只能选择这一套表达方式，避免能力配置在 JSON、独立表和模型字段之间漂移。

### 7.1 ProviderConfig

字段：

- `id`。
- `provider_type`。
- `display_name`。
- `base_url`。
- `auth_type`。
- `api_key_id`。
- `default_model`。
- `capabilities`。
- `timeout_seconds`。
- `rate_limit_policy`。
- `streaming_enabled`。
- `tool_calling_enabled`。
- `is_active`。
- `created_at`。
- `updated_at`。

### 7.2 ModelConfig

字段：

- `id`。
- `provider_id`。
- `model_id`。
- `display_name`。
- `context_window`。
- `supports_streaming`。
- `supports_tool_calling`。
- `supports_json_mode`。
- `supports_vision`。
- `supports_embeddings`。
- `is_default`。
- `is_active`。

### 7.3 ProviderHealthCheck

字段：

- `id`。
- `provider_id`。
- `status`。
- `checked_at`。
- `latency_ms`。
- `error_code`。
- `error_message`。
- `model_tested`。

迁移规则：

- schema 变更使用 Alembic。
- 应用启动只执行 Alembic `upgrade head`，随后从兼容的 Kimi/DeepSeek API Key 启动映射 ProviderConfig；启动流程不得用 `Base.metadata.create_all` 掩盖迁移缺口。
- 现有 API Key 必须继续可读。
- 如果引入 ProviderConfig，现有 Kimi/DeepSeek key 需要迁移或映射到 preset Provider。

## 8. LLM Provider 架构

### 8.1 目标

- 从 Task 执行路径中移除硬编码 Provider 分支。
- 支持官方 API 和第三方 OpenAI-compatible 中转站。
- 归一化 Provider 失败。
- 不改代码即可配置 model 和 capability。

### 8.2 内部接口

核心代码依赖统一接口：

```text
ProviderAdapter
  - chat(request) -> ChatResponse
  - stream(request) -> AsyncIterator[ChatChunk]
  - list_models() -> list[ModelInfo]
  - test_connection(model_id) -> ProviderHealthResult
  - normalize_error(error) -> ProviderError
```

标准 request 字段：

- `messages`。
- `model`。
- `temperature`。
- `max_tokens`。
- `tools`。
- `tool_choice`。
- `response_format`。
- `stream`。
- `metadata`。

标准 response 字段：

- `content`。
- `tool_calls`。
- `finish_reason`。
- `usage`。
- `raw_provider_response` 只允许在 debug-safe 路径使用。

### 8.3 Provider Registry

Registry 职责：

- 保存内置 Provider presets。
- 将 ProviderConfig 解析为 Adapter。
- 暴露 capability matrix。
- 提供 default models。
- 保存前校验 config。
- 仅在显式配置时选择 fallback Provider。

Provider type 示例：

- `openai`。
- `anthropic`。
- `gemini`。
- `deepseek`。
- `moonshot`。
- `dashscope`。
- `zhipu`。
- `qianfan`。
- `hunyuan`。
- `minimax`。
- `openai_compatible`。

### 8.4 官方 Provider Adapter

官方 API 兼容目标：

- OpenAI。
- Anthropic Claude。
- Google Gemini。
- DeepSeek。
- Moonshot/Kimi。
- Alibaba DashScope/Qwen。
- Zhipu GLM。
- Baidu Qianfan。
- Tencent Hunyuan。
- MiniMax。

Adapter 规则：

- 必要时遵循官方 API 语义。
- 官方 SDK 仅在能显著降低复杂度时引入。
- Provider-specific response shape 必须隐藏在标准 response 后。
- 每个 Adapter 记录不支持能力。

当前实现：

- `ProviderAdapterResolver` 位于 `backend/agent_forge/core/providers/resolver.py`，负责将 `ProviderConfig` 解析到具体 `ProviderAdapter`。
- resolver 当前覆盖 Relay Provider、首批官方 Provider Adapter 和 planned Provider placeholder。
- `ProviderAdapterBackedLLMProvider` 位于 `backend/agent_forge/core/llm_client.py`，将现有 `LLMRouter` provider 接口桥接到 `ProviderAdapter`；默认 Kimi/DeepSeek provider 注册和 API key manager refresh 已通过 `ProviderAdapterResolver` 解析后委托 Adapter。
- `KimiProvider`、`DeepSeekProvider` 旧实现已从 `llm_client.py` 和 `agent_forge.core` 导出中移除；Kimi/DeepSeek 行为由 Provider preset、`ProviderAdapterResolver` 和官方 OpenAI-compatible Adapter 承接。
- `OpenAICompatibleOfficialAdapter` 位于 `backend/agent_forge/core/providers/official.py`，复用 OpenAI-compatible chat completion transport。
- 当前已覆盖 OpenAI、DeepSeek、Moonshot/Kimi 这类官方 OpenAI-compatible API 的 chat、usage 和归一化错误行为。
- `AnthropicOfficialAdapter` 位于 `backend/agent_forge/core/providers/official.py`，使用 Anthropic Messages API 语义，覆盖 chat、stream text delta、usage 和归一化错误行为。
- `GeminiOfficialAdapter` 位于 `backend/agent_forge/core/providers/official.py`，使用 Gemini generateContent API 语义，覆盖 chat、stream text chunk、usage 和归一化错误行为。
- `DashScopeOfficialAdapter` 位于 `backend/agent_forge/core/providers/official.py`，使用 DashScope OpenAI-compatible mode 官方路径，覆盖 chat、stream chunk、usage 和归一化错误行为。
- Zhipu GLM、Baidu Qianfan、Tencent Hunyuan、MiniMax 当前是 `planned` preset，capability defaults 全为 false。
- `PlannedProviderAdapter` 位于 `backend/agent_forge/core/providers/planned.py`，planned Provider 被误调用时返回 `provider_unsupported_feature`，不触发供应商请求。
- 第二批完整 Adapter 实现前必须重新核对官方 API 文档：Zhipu `https://docs.bigmodel.cn/`，Qianfan `https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html`，Hunyuan `https://cloud.tencent.com/document/product/1729`，MiniMax `https://platform.minimaxi.com/document`。

### 8.5 Relay Provider Adapter

Relay 目标：

- OpenRouter。
- One API / New API。
- LiteLLM Proxy。
- 自定义 OpenAI-compatible Base URL。

行为：

- Base URL 可配置。
- 默认使用 OpenAI-compatible chat completion 语义。
- 允许自定义 model ID。
- endpoint 支持时探测 model list。
- 探测失败时允许手动录入 model。
- 可选 header 只能通过安全、文档化配置加入。

当前实现：

- Relay Adapter 位于 `backend/agent_forge/core/providers/relay.py`，共享 Adapter contract 位于 `backend/agent_forge/core/providers/adapter.py`。
- OpenAI-compatible shared transport 位于 `backend/agent_forge/core/providers/openai_compatible.py`，供 Relay Adapter 和 OpenAI-compatible 官方 Adapter 复用。
- Relay Adapter 使用 mocked `httpx` response 测试 chat、stream chunk、model list、connection test 和 error normalization，不依赖真实 Provider 调用。
- Relay Adapter 的归一化错误不得包含 API Key、Authorization header 或其他 secret。

非目标：

- 自动化 Provider 官网、控制台或网页聊天 UI。

### 8.6 Capability Matrix

每个 Provider/Model 对需要声明：

- `chat`。
- `streaming`。
- `tool_calling`。
- `json_mode`。
- `vision`。
- `embeddings`。
- `model_listing`。
- `usage_reporting`。

Execution 代码请求功能前必须检查 capability。Provider 级默认能力来自 `ProviderConfig.capabilities`，模型级覆盖来自 `ModelConfig.supports_*`。当二者冲突时，以模型级能力为准。

### 8.7 错误归一化

Provider error category：

- `provider_auth_failed`。
- `provider_rate_limited`。
- `provider_model_not_found`。
- `provider_timeout`。
- `provider_network_error`。
- `provider_invalid_request`。
- `provider_unsupported_feature`。
- `provider_quota_exceeded`。
- `provider_server_error`。
- `provider_unknown_error`。

错误响应包含：

- category。
- provider id/type。
- 安全时包含 model id。
- retryable flag。
- 用户安全 message。
- 不含 secret 的 debug details。

## 9. 安全与 secret

规则：

- API Key 加密存储。
- 明文 API Key 不进入日志。
- 前端只接收 masked key。
- `/api/v1/keys` 支持按 Provider 标识过滤；key 列表和删除响应只返回 masked key 与 linked ProviderConfig 摘要，不返回明文 key 或 encrypted key。
- 删除 API Key 时响应必须提示 linked ProviderConfig 的影响，便于前端展示确认或结果提示。
- `APIKeyManager` 使用 `ProviderRegistry` 解析 provider type 和 preset alias；`get_all_keys()` 不再硬编码 Kimi/DeepSeek 列表，但 Moonshot/Kimi 仍以 `kimi` 兼容键返回给现有启动路径。
- Provider test 错误不得回显 request header。
- Secret 通过安全 manager API 在调用时提供给 Adapter。
- 生产环境必须设置 `JWT_SECRET_KEY` 和 `ENCRYPTION_KEY`。
- `.env.example` 只写变量名和说明，不写真实值。

## 10. Memory 架构

当前决策：

- embedded Chroma persistent client 是主要 Memory vector store。
- Chroma data path 作为 backend storage 挂载。
- Chroma 不可用时 SQLite fallback 继续可用。

规则：

- Memory 不是 Knowledge Base。
- Memory Retrieval 属于 Execution context building。
- 存储拓扑是实现细节，不泄露到产品语言。
- Vector store 失败必须受控 fallback 或明确报错。

## 11. Metrics 与可观测性

后端应记录：

- Task 状态计数。
- Task duration。
- Agent calls 和 latency。
- Provider id/type。
- Model id。
- 可用时记录 token usage。
- 归一化 Provider error。
- 可用时记录 system health。

不得记录：

- 明文 API Key。
- metrics 表中的敏感 prompt 内容。
- 默认情况下的完整 provider raw response。

Current implementation:
- `LLMRouter.route()` records safe Provider metrics for the active Task when a Task execution context is bound.
- Metrics are appended to `TaskORM.task_metadata.provider_metrics` as a whitelisted record: `provider`, `model`, `latencyMs`, `inputTokens`, `outputTokens`, `totalTokens`, `status`, and normalized `errorCategory`.
- `MetricsService.append_provider_metric()` rejects malformed records and never persists prompt text, API Key material, Authorization headers, or raw Provider responses.
- `GET /api/v1/metrics/providers` returns a standard envelope with Provider/model call counts, failures, average latency, token totals, and error-category counts.
- `frontend/src/api/metrics.ts` exposes `fetchProviderMetrics()` and `toProviderMetrics()` so frontend callers consume typed, sanitized Provider metric objects.

## 12. 配置

环境变量：

- `ENVIRONMENT`。
- `DEBUG`。
- `DB_TYPE`。
- `DATABASE_URL`。
- `JWT_SECRET_KEY`。
- `JWT_ALGORITHM`。
- `JWT_EXPIRE_DAYS`。
- `ENCRYPTION_KEY`。
- `ENCRYPTION_SALT`。
- `REDIS_URL`。
- `CHROMA_PERSIST_DIR`。
- 为兼容保留的 Provider bootstrap 变量。

Provider 配置应逐步转向数据库中的 ProviderConfig，同时保留本地开发的环境变量 bootstrap 兼容。

## 13. 测试策略

后端：

- Provider registry 与 adapter 单元测试。
- API key 加密和掩码测试。
- 错误归一化测试。
- Memory fallback 测试。
- 新增 `/api/v1/providers` 后添加 route tests。
- 保持现有 Task/Agent route tests。

前端：

- Provider settings form 组件测试。
- Store API response normalization 测试。
- Task status 和 Step timeline 渲染测试。
- 错误状态和空状态测试。

集成：

- 使用 mock Provider adapter 做确定性测试。
- 使用 fake local HTTP server 或 mocked `httpx` 测试 OpenAI-compatible relay。
- 可行时测试 SSE stream 行为。

验证命令：

```powershell
cd backend
python -m pytest
python -m mypy agent_forge --ignore-missing-imports
python -m flake8 agent_forge
```

```powershell
cd frontend
npm run lint
npm run test
npm run build
```

## 14. 兼容规则

- 保留 `/api/v1` 路径，除非明确记录迁移。
- 保留当前 Task status。
- 保留内置可执行 Agent role name：`researcher`、`coder`、`writer`、`reviewer`、`executor`。
- `planner` 是 planning component，不属于 `AgentRole`，不得作为可执行 Agent 或 Agent-to-Agent message receiver 暴露。
- 保留当前本地开发路径，除非明确记录。
- 通过 Alembic 保留现有数据。
- 不移除 SQLite 开发支持。
- 不在没有新 ADR 的情况下把 embedded Chroma 改成独立服务。

## 15. 文档规则

实现改变产品行为时：

- 产品范围或用户流程变化：更新 `docs/PRD.md`。
- UI、导航、视觉或交互变化：更新 `docs/DESIGN.md`。
- API、架构、数据、Provider、部署或质量门禁变化：更新 `docs/TECH.md`。
- issue 范围或顺序变化：更新 `docs/SPEC.md`。
- 开发流程变化：更新 `AGENTS.md`。
