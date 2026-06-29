# AgentForge 重构任务规格

## 1. 目的

本文档将 PRD 转换为后续工程 issue。它面向实现 Agent 和开发者。每个 issue 都应能独立理解，并包含背景、目标、影响范围、验收标准和验证方式。

本文档不追踪 issue 状态；执行时使用项目 issue tracker 或实现分支记录状态。

## 2. 全局验收标准

所有重构任务必须保留：

- 单租户、个人开发者产品范围。
- 现有 `/api/v1` 兼容性，除非明确迁移。
- 现有 Task、Agent、Step、Memory、User、API Key 数据。
- Memory 与 Future Scope Knowledge Base 的清晰边界。
- 不做 LLM 供应商官网网页 UI 自动化。
- API Key 加密存储。
- 前端路由保护。

所有代码变更需要通过：

- 后端：`python -m pytest`、`python -m mypy agent_forge --ignore-missing-imports`、`python -m flake8 agent_forge`。
- 前端：`npm run lint`、`npm run test`、`npm run build`。

## 3. Issue 清单

### AF-001 建立文档权威来源

背景：

仓库里存在旧计划和历史 spec，重构需要当前权威文档集。

目标：

让 PRD、DESIGN、TECH、SPEC、AGENTS 成为后续工作的权威来源。

影响范围：

- 仅文档。

任务：

- 需要时从 README 链接到新文档。
- 后续文档更新时标记旧 implementation plans 为历史资料。
- 确保 AGENTS 指向 PRD、DESIGN、TECH、SPEC。

验收标准：

- 新文档在产品范围和术语上保持一致。
- 当前范围文档不把 AgentForge 描述成团队工作区、Knowledge Base 或电商产品。

验证：

- 检查团队、管理员、Knowledge Base、网页自动化等术语只出现在非目标、Future Scope、术语解释或避免使用说明中，未被描述为当前能力。
- 检查 README 文档链接。

依赖：

- 无。

### AF-002 统一前后端领域类型

背景：

当前后端和前端类型有重叠，但缺少统一契约。

目标：

对齐 Task、Agent、Step、Memory、User、API Key、Provider、Metric 类型。

影响范围：

- 后端 Pydantic schema。
- 前端 `src/types`。
- Store mapping function。

任务：

- 审计当前 response shape。
- 定义前端领域类型命名。
- 需要兼容时保留 legacy field mapping。
- 为 mapping function 添加测试。

验收标准：

- 前端组件不依赖未经类型化的原始 backend payload。
- status enum 与后端值一致。
- 类型转换显式可查。

验证：

- 后端 schema 测试。
- 前端 store 测试。
- `npm run build`。

依赖：

- AF-001。

### AF-003 标准化 API 响应和错误 Envelope

背景：

统一 success/error envelope 可以减少前端特殊分支。

目标：

新 route 和被触碰 route 逐步使用标准 `success/data/message` 与 `success/error` 结构。

影响范围：

- FastAPI route helper。
- 前端 API client。
- Store error handling。

任务：

- 在保持当前前端兼容的前提下增加标准 response helper。
- 归一化 error code。
- 将后端 error 映射成用户安全 message。
- 记录 legacy route 迁移预期。

验收标准：

- 新 Provider route 使用标准 envelope。
- 现有 Task 和 Agent 行为不被破坏。
- error details 不包含 secret。

验证：

- route success/failure tests。
- 前端 API client tests。

依赖：

- AF-002。

### AF-004 增加 Provider Registry 领域模型

背景：

当前 LLM client 偏 provider-specific，无法支撑广泛配置。

目标：

建立 Provider Registry，用于解析 Provider config 到 Adapter，并暴露 capability metadata。

影响范围：

- 后端 Provider core module。
- 后续数据库 schema。
- Settings UI。

任务：

- 定义 Provider type enum 或 constants。
- 定义 ProviderConfig model。
- 定义 ModelConfig model。
- 定义 capability flags。
- 添加内置 Provider presets。
- 添加官方 Provider 与 relay Provider 的校验规则。

验收标准：

- Registry 能列出内置 Provider presets。
- Registry 能校验自定义 OpenAI-compatible relay config。
- Capability flags 明确。

验证：

- Registry validation 单元测试。
- Built-in presets 单元测试。

依赖：

- AF-002。

### AF-005 增加 Provider 持久化与迁移

背景：

Provider 配置需要持久化，并且不能丢失当前 key。

目标：

持久化 ProviderConfig、ModelConfig、ProviderHealthCheck，同时保留现有 API Key 数据。

影响范围：

- SQLAlchemy models。
- Alembic migration。
- API key manager。

任务：

- 添加 ProviderConfig、ModelConfig、ProviderHealthCheck ORM。
- 不新增独立 ProviderCapability ORM；能力保存在 `ProviderConfig.capabilities` 和 `ModelConfig.supports_*` 字段。
- 创建 Alembic migration。
- 将 API key 与 Provider config 关联。
- 将现有 Kimi/DeepSeek key 映射到 preset Provider 或兼容记录。

验收标准：

- 迁移后现有 APIKey 记录继续可读。
- Provider config 可创建和查询。
- Capability 只有 `ProviderConfig.capabilities` 和 `ModelConfig.supports_*` 两个权威来源。
- migration 兼容 SQLite 和 PostgreSQL。

验证：

- migration 测试或手动 upgrade 检查。
- 后端 persistence 单元测试。

依赖：

- AF-004。

### AF-006 实现 OpenAI-Compatible Relay Adapter

背景：

第三方中转站是最灵活的兼容路径。

目标：

支持自定义 OpenAI-compatible Base URL，包括 OpenRouter、One API/New API、LiteLLM Proxy。

影响范围：

- Provider adapters。
- LLM client refactor。
- Provider settings。

任务：

- 使用 OpenAI-compatible chat completion 语义实现 relay adapter。
- 支持可配置 Base URL 和 model ID。
- 支持 streaming 开关。
- 支持 tool calling 开关。
- endpoint 支持时探测 model list。
- 探测失败时允许手动模型配置。

验收标准：

- 使用 mocked endpoint 时，自定义 Base URL + API key + model ID 可通过连接测试。
- Relay adapter 归一化 success、stream chunks、usage、errors。
- 不使用供应商网站自动化。

验证：

- mocked HTTP response 单元测试。
- error normalization 测试。

依赖：

- AF-004。

### AF-007 实现首批官方 Provider Adapter

背景：

AgentForge 需要通过 Adapter 支持主要官方 API。

目标：

实现或搭建首批官方 Provider Adapter。

影响范围：

- Provider adapters。
- Provider registry presets。
- Tests。

首批：

- OpenAI。
- Anthropic Claude。
- Google Gemini。
- DeepSeek。
- Moonshot/Kimi。
- Alibaba DashScope/Qwen。

任务：

- 添加 adapter modules。
- 记录每个 Adapter 的 base URL、auth、streaming、tool calling、model listing、不支持能力。
- 为支持的 Adapter 实现最小 chat request 行为。
- 使用 mock 测试，不依赖真实 API 调用。

验收标准：

- 每个首批 Provider 都有 registry preset。
- 每个 Adapter 都有 request mapping 和 error normalization 的确定性测试。
- 不支持能力通过 capability 标记，而不是默认假设支持。

验证：

- 后端 adapter 单元测试。
- mypy 和 flake8。

依赖：

- AF-004。
- AF-006 中可复用的 OpenAI-compatible 行为。

### AF-008 搭建第二批官方 Provider Adapter

背景：

其他官方 Provider 已列入计划，但 API 语义可能不同。

目标：

为剩余官方目标创建文档化 adapter scaffold 和 preset，不夸大未测试能力。

影响范围：

- Provider registry。
- Provider docs。

第二批：

- Zhipu GLM。
- Baidu Qianfan。
- Tencent Hunyuan。
- MiniMax。

任务：

- 添加 Provider presets。
- 添加 capability defaults。
- 添加 adapter interface 或 placeholder，未实现能力返回 `provider_unsupported_feature`。
- 记录完整实现前需要查阅的官方 API 信息。

验收标准：

- UI 可按实现状态展示这些 Provider。
- Execution 不会误路由到未实现 adapter。

验证：

- Registry tests 验证 implemented/planned 状态。

依赖：

- AF-004。

### AF-009 将 LLM Client 重构为 Adapter 架构

背景：

Task execution 不应知道具体 Provider 细节。

目标：

让 `llm_client` 使用 Provider Registry 和 ProviderAdapter，而不是硬编码 provider 分支。

影响范围：

- `backend/agent_forge/core/llm_client.py`。
- Agent execution loop。
- Provider services。
- Tests。

任务：

- 引入标准 request/response 类型。
- 调用前解析 ProviderConfig。
- 将请求委托给 Adapter。
- 通过 preset 保留现有 Kimi/DeepSeek 行为。
- 归一化 Provider errors。

验收标准：

- 使用当前 Kimi/DeepSeek 配置时，现有 Task execution 继续工作。
- 新 relay Provider 不需要修改 Agent 代码即可使用。
- Provider capability 错误明确可读。

验证：

- 更新现有 LLM client tests。
- 使用 mock provider 添加 adapter integration tests。
- 使用 mock adapter 做 Task execution smoke test。

依赖：

- AF-004。
- AF-006。

### AF-010 扩展 API Key 管理以支持 Provider

背景：

API Key 已存在，但需要 Provider-aware 行为。

目标：

让 API Key 管理按 Provider 维度工作，并兼容 ProviderConfig。

影响范围：

- API key manager。
- Keys API routes。
- Database model/migration。
- Settings UI。

任务：

- 将 key 关联到 provider type/config。
- 保持加密存储。
- 保持掩码展示。
- 记录 usage count 和 last used。
- 添加 provider-aware validation。

验收标准：

- 可以按 Provider 列出 keys。
- 删除 key 时清楚提示关联 Provider config 的影响。
- API response 和日志中不出现明文 key。

验证：

- API key manager tests。
- Key CRUD route tests。

依赖：

- AF-005。

### AF-011 增加 Provider API Routes

背景：

前端 Settings 需要后端 route 管理 Provider 配置。

目标：

添加 `/api/v1/providers` routes。

影响范围：

- 后端 routes。
- Schemas。
- Provider registry/service。

Routes：

- `GET /api/v1/providers/presets`。
- `GET /api/v1/providers`。
- `POST /api/v1/providers`。
- `GET /api/v1/providers/{provider_id}`。
- `PATCH /api/v1/providers/{provider_id}`。
- `DELETE /api/v1/providers/{provider_id}`。
- `POST /api/v1/providers/{provider_id}/test`。
- `GET /api/v1/providers/{provider_id}/models`。

验收标准：

- Routes 使用标准 envelope。
- 需要登录认证。
- Test route 返回归一化 health result。
- Model listing 失败时可优雅降级并提示手动录入。

验证：

- Route tests 覆盖 success、auth failure、validation failure、provider test failure。

依赖：

- AF-004。
- AF-005。
- AF-010。

### AF-012 构建 Provider Settings UI

背景：

用户应能不改环境变量就配置 Provider。

目标：

在 Settings 中添加官方 Provider preset 和自定义 relay Provider 配置界面。

影响范围：

- `frontend/src/pages/Settings.tsx`。
- Frontend API client。
- Stores 和 types。
- UI components。

任务：

- 展示 Provider 列表和健康状态。
- 从 preset 添加官方 Provider。
- 添加 custom relay Provider 流程。
- 添加 API Key 输入，保存后掩码。
- 添加 Test Connection 操作。
- 添加 model select/manual model entry。
- 展示 capability flags。

验收标准：

- 用户可以创建自定义 OpenAI-compatible Provider config。
- 用户可以测试 Provider 并看到成功/失败详情。
- Key 保存后不展示明文。
- UI 覆盖 loading、empty、error、validation 状态。

验证：

- Component tests。
- Store tests。
- `npm run build`。

依赖：

- AF-011。
- AF-019。

### AF-013 规范 Task Execution Timeline

背景：

Task detail 应是 Execution 检查的权威页面。

目标：

确保 Step stream、persist、sort、render 一致。

影响范围：

- Task routes。
- Step persistence。
- Task store。
- TaskDetail UI。

任务：

- 确认 Step order 稳定。
- 防止 SSE 重连产生重复 Step。
- 统一 Step type label 和 color。
- 清晰渲染 error Step。

验收标准：

- 用户可以在 Task detail 理解 Execution 进展。
- stream 重连不重复 Step。
- Step label 与 PRD 一致。

验证：

- 后端 Step tests。
- 前端 TaskDetail tests。

依赖：

- AF-002。

### AF-014 澄清 Planner 与 Agent 边界

背景：

当前范围中 Planner 不是内置可执行 Agent。

目标：

统一后端 enum、UI 文案和文档中 Planner 作为组件的定位。

影响范围：

- Agent role types。
- Planner 代码注释和文档。
- Agent Monitor UI。

任务：

- 审计 role enum 使用。
- 保持 Planner output 在 Task planning 中可见。
- 除内部实现必要外，不把 Planner 渲染为五个内置 Agent worker。

验收标准：

- UI 列出五个内置可执行 Agent。
- Planner 作为 planning component 可见。
- 文档和代码注释不与 PRD 矛盾。

验证：

- 可行时添加类型测试或单元测试。
- UI component check。

依赖：

- AF-002。

### AF-015 改进 Dashboard 产品状态

背景：

Dashboard 应汇总状态并引导用户进入下一步。

目标：

让 Dashboard 反映 Task、Agent、Provider、system health。

影响范围：

- Dashboard UI。
- Metrics store/API。
- Provider health data。

任务：

- 展示 Task status counts。
- 展示 Agent summary。
- 没有 active healthy Provider 时展示 warning。
- 展示 recent Tasks。
- 增加 empty/degraded/error 状态。

验收标准：

- 新用户看到明确下一步。
- Provider 配置问题在 Task 失败前可见。
- Dashboard 保持可扫描。

验证：

- 前端 component tests。
- 桌面和移动端手动检查。

依赖：

- AF-011。
- AF-013。
- AF-016。

### AF-016 增加 Provider 可观测指标

背景：

Provider/model 失败和延迟是调试关键。

目标：

记录 provider、model、latency、usage、归一化失败类别，同时避免敏感内容泄露。

影响范围：

- Metrics service。
- Provider adapters。
- Metrics API。
- Dashboard/charts。

任务：

- 在相关 metrics 中添加 provider/model 字段。
- 可用时记录 token usage。
- 记录 normalized error category。
- 排除明文 prompt 和 key。

验收标准：

- Metrics 能回答哪个 Provider/model 失败。
- 不持久化敏感数据。
- 现有 metrics 继续可用。

验证：

- Metrics service unit tests。
- Metrics route tests。

依赖：

- AF-009。
- AF-011。

### AF-017 强化 Memory 边界

背景：

Memory 和 Knowledge Base 容易混用。

目标：

保持 Memory 聚焦执行上下文和检索。

影响范围：

- Memory manager。
- UI labels。
- Docs。

任务：

- 审计 label 和 comments。
- 确保 Memory Retrieval 被描述为 Memory 的一部分。
- 当前 UI 不加入用户管理 Knowledge Base。

验收标准：

- 当前 UI 不把 Memory 称作 Knowledge Base。
- Memory 失败行为明确。

验证：

- 搜索 UI/docs 中错误的 Knowledge Base 用法。
- 后端 Memory tests 继续通过。

依赖：

- AF-001。

### AF-018 标准化前端设计 Token

背景：

UI 应保持深色技术控制台，并有明确语义色。

目标：

围绕 DESIGN.md 整理 Tailwind token 和组件样式。

影响范围：

- Tailwind config。
- Global CSS。
- UI primitives。

任务：

- 定义 surface/text/brand/semantic color tokens。
- 确保 badge 使用语义状态色。
- 安全时移除未使用的模板 CSS。
- 圆角保持 8px 或更小。

验收标准：

- Dashboard、Tasks、Agents、Chat 的状态色一致。
- UI 不再像单一蓝紫色界面。
- 文本可读。

验证：

- 前端 component tests。
- 桌面和移动端视觉 QA。

依赖：

- AF-001。

### AF-019 加固前端 API Client 与 Store

背景：

API 兼容和错误归一化需要清晰的数据边界。

目标：

让 API parsing 和 mapping 不散落在展示组件中。

影响范围：

- `frontend/src/api`。
- Zustand stores。
- Frontend tests。

任务：

- 集中处理 response envelope。
- 显式映射 snake_case/camelCase。
- 集中归一化 error。
- 确保 SSE setup/cleanup 安全。

验收标准：

- Component 接收 typed domain objects。
- API error 展示统一消息。
- 组件卸载时 EventSource 被关闭。

验证：

- Store tests。
- Error state component tests。

依赖：

- AF-003。

### AF-020 增加开发护栏

背景：

项目需要面向 Agent 和开发者的质量门禁。

目标：

让 AGENTS/CLAUDE 可操作，并让后续变更与文档保持一致。

影响范围：

- 根目录 agent instruction docs。
- 开发流程。

任务：

- AGENTS 作为权威 instruction file。
- CLAUDE 只指向 AGENTS 并保留少量提醒。
- 产品/API/设计变更需要更新 docs。
- 按变更类型要求后端/前端验证。

验收标准：

- 后续 Agent 知道在哪里找产品和技术规则。
- CLAUDE 不复制一份会漂移的完整规则。

验证：

- Review AGENTS 和 CLAUDE。

依赖：

- AF-001。

## 4. 建议执行顺序

1. AF-001、AF-020。
2. AF-002、AF-003、AF-019。
3. AF-004、AF-005。
4. AF-006、AF-007、AF-008。
5. AF-009、AF-010、AF-011。
6. AF-013、AF-014、AF-016、AF-017、AF-018。
7. AF-012、AF-015。

该顺序依次处理文档权威、领域/API/前端数据边界、Provider 基础设施、后端集成、执行与可观测性基础、再到 Provider Settings UI 和 Dashboard 展示，减少跨层返工。
