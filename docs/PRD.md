# AgentForge 产品需求文档

## 1. 产品定位

AgentForge 是面向个人开发者的单租户、多智能体任务执行与可观测平台。用户可以创建 Task，由 Planner 拆解任务，再交给不同 Agent 执行，并在执行过程中查看 Step、结果、错误和可复用的 Memory。

本文档是 AgentForge 重构目标版的产品口径来源。旧的实施计划和历史 spec 只作为背景资料；当旧文档与本文档冲突时，以本文档为准。

## 2. 目标用户

主要用户：

- 个人开发者，在本地或私有环境中运行 AgentForge。
- 希望把复杂任务委托给多个 AI Agent 协作完成。
- 需要知道 Agent 正在做什么、为什么这样做、最终产出是什么。
- 关心模型供应商灵活性、执行过程可观察性、数据隐私和可重复的开发流程。

非主要用户：

- 团队管理员、组织所有者、企业运维人员。
- 使用 AgentForge 托管 SaaS 的外部客户。
- 需要强引导消费级体验的非技术用户。

## 3. 产品目标

- 提供从 Task 创建到结果复盘的稳定执行闭环。
- 让 Planner 和 Agent 行为足够可观察，便于调试和建立信任。
- 将执行中有价值的上下文沉淀为 Memory，但不把 Memory 扩展成完整 Knowledge Base 产品。
- 通过官方 API 和 OpenAI-compatible 第三方中转站支持多种 LLM Provider。
- 保持产品边界足够克制，适合个人开发者单租户部署。
- 在代码重构前建立清晰的产品、设计、技术和开发规范。

## 4. 非目标与未来范围

以下能力属于 Future Scope，不得描述为当前能力：

- 团队工作区、组织空间、多租户协作。
- 管理员用户角色和角色权限系统。
- 插件市场、公开工具市场、社区扩展商店。
- PWA、离线优先体验。
- 国际化。
- 用户自行上传和管理资料的 Knowledge Base。
- 完整的多次运行历史和独立 Execution run 记录。
- 计费、订阅、用量收费、SaaS 账号体系。
- 官方网站网页端自动化。AgentForge 只集成官方 API 和 OpenAI-compatible API，不自动化 ChatGPT、Claude、Gemini 等网页 UI。

## 5. 领域术语

| 术语 | 含义 | 避免使用 |
| --- | --- | --- |
| AgentForge | 用于编排 AI Agent 完成用户 Task 的产品上下文。 | 企业协作平台 |
| User | 在单租户环境中使用 AgentForge 的认证用户。 | 管理员、团队成员 |
| Task | 用户请求的一项工作，可以被规划、执行、观察和复盘。 | 项目、工单、Job |
| Planner | 将 Task 拆解为可分配工作的组件。 | Planner Agent |
| Agent | 执行特定角色工作的 AI Worker。 | Bot、Service |
| Execution | 将 Task 转化为 Agent 行动和结果的生命周期。 | Pipeline、Run 记录 |
| Step | Execution 过程中的可观察事件，如 thought、action、observation、final、error。 | 单纯日志 |
| Memory | Agent 可在后续 Execution 中复用的任务上下文。 | Knowledge Base |
| Memory Retrieval | Agent 查找相关 Memory 的机制。 | 独立 RAG 产品 |
| Knowledge Base | 未来的用户管理资料库。 | 当前 Memory |
| Provider | LLM 服务配置和 Adapter 目标。 | 写死的模型 |
| Relay Provider | 第三方 OpenAI-compatible API 中转站或网关。 | 网页自动化 |
| API Key | 用于访问 LLM Provider 或 AgentForge API 的凭证。 | 用户角色 |

## 6. 当前产品范围

### 6.1 认证

AgentForge 保持轻量认证：

- 用户可以通过用户名、邮箱和密码注册。
- 用户可以通过用户名和密码登录。
- 前端持久化 JWT 登录状态。
- 应用内页面需要登录后访问。
- 当前目标版本不引入管理员角色。

验收标准：

- 未登录用户只能访问 Login 和 Register。
- 已登录用户可以访问 Dashboard、Tasks、Agents、Chat、Settings。
- 认证错误信息统一、可读，不暴露内部细节。

### 6.2 Dashboard

Dashboard 是系统总览和入口页。

需要展示：

- Task 状态汇总。
- Agent 可用性和当前活动。
- 最近 Task。
- 关键执行信号。
- Provider 健康状态或配置提醒。

验收标准：

- 用户可以在一屏内理解系统健康状态。
- Dashboard 负责汇总和跳转，不成为唯一操作入口。
- 空状态、加载状态、错误状态、后端降级状态明确可见。

### 6.3 Tasks

Task 是 AgentForge 的核心产品对象。

需要支持：

- 创建 Task，包含标题、描述，必要时包含优先级。
- 列出 Task，展示状态、优先级、创建时间、更新时间和摘要。
- 打开 Task detail。
- 在后端支持时取消 pending、planning、executing 状态的 Task。
- 保存 Task 结果和错误信息。

Task 状态：

- `pending`：已创建但尚未开始。
- `planning`：Planner 正在拆解 Task。
- `executing`：Agent 正在执行 Task。
- `completed`：已生成最终结果。
- `failed`：Execution 失败。
- `cancelled`：用户或系统取消 Execution。

验收标准：

- 状态标签与后端枚举一致。
- 用户能判断 Task 是否待处理、运行中、完成、失败或取消。
- Task detail 是查看 Step timeline 和结果的权威页面。

### 6.4 Planner

Planner 不是 Agent。它是负责任务拆解和分配准备的组件。

需要支持：

- 将 Task 拆解为有顺序或依赖关系的计划节点。
- 在可行时为节点分配 Agent role。
- 输出可观察的规划 Step 或规划摘要。
- 失败时返回可行动的错误信息。

验收标准：

- 文档和 UI 不把 Planner 计入可执行 Agent 列表。
- Planner 输出可以在 Task detail 或 Execution timeline 中检查。

### 6.5 Agents

目标内置可执行 Agent：

- Researcher：搜集、整理和总结信息。
- Coder：生成、分析或修改代码相关内容。
- Writer：撰写和润色文本。
- Reviewer：审查和批判输出。
- Executor：执行最终行动或动作导向任务。

需要支持：

- 展示 Agent 名称、角色、状态、当前模型或 Provider。
- 展示当前 Task。
- 通过轮询或 SSE 观察 Agent 状态变化。
- 在后端支持时发送 Agent 消息。

验收标准：

- Agent 状态为 `idle`、`busy`、`error`。
- Agent role 与后端枚举一致。
- Agent Monitor 区分当前 Agent 状态和历史 Task Step。

### 6.6 Execution Steps

Step 让 Execution 过程可检查。

Step 类型：

- `thought`：可展示的思考或计划信息。
- `action`：工具调用或 Agent 行动。
- `observation`：行动或工具返回的观察结果。
- `final`：最终答案或产出。
- `error`：失败事件。

需要支持：

- 为 Task 持久化 Step。
- 后端可用时通过 SSE 将新 Step 推送给前端。
- 按稳定序号或时间排序。
- 展示 Step 类型、Agent role、内容和时间。

验收标准：

- 用户不需要读服务端日志，也能理解 Execution 发生了什么。
- 失败 Step 显示原因和受影响的 Agent 或工具。

### 6.7 Chat

Chat 是辅助交互入口，不是 AgentForge 的主产品模型。

需要支持：

- 用户从 Chat 输入 Task 描述，并创建真实 Task。
- 创建成功后链接到对应 Task detail。
- 在可用时展示相关 Task 或 Step 上下文。
- 与 Task 执行术语保持一致。

验收标准：

- Chat 不引入与 Task 竞争的独立产品模型。
- Chat 触发或引用 Task 时，需要能链接到对应 Task。
- Chat 不展示模拟 Agent 回复或伪造 Step；Execution 的权威记录仍在 Task detail。

### 6.8 Memory

Memory 是 Execution 中产生或使用的可复用上下文。

需要支持：

- 保存 Memory 内容、类型、关联 Agent、关联 Task、来源、元数据、创建时间。
- 为 Agent 检索相关 Memory。
- 使用 embedded Chroma 作为主要向量存储。
- Chroma 不可用时支持 SQLite fallback。

验收标准：

- UI 和文档不把 Memory 称为 Knowledge Base。
- Memory Retrieval 被描述为 Memory 的一部分，而不是单独的文档问答产品。
- Memory 存储失败时提供明确错误或受控 fallback。

### 6.9 Metrics 与可观测性

AgentForge 应提供足够信息帮助开发者诊断本地运行。

需要支持：

- Task 指标：按状态汇总、耗时、成功失败情况。
- Agent 指标：状态、调用次数、延迟。
- Provider 与模型指标：provider、model、latency、token usage、失败类别。
- 系统指标：CPU、内存、运行状态。

隐私规则：

- 不保存或展示明文 API Key。
- 不在 metrics 中记录敏感 prompt 内容。
- 可以记录 Task ID、provider、model、latency、token 数、状态、归一化错误类别。

### 6.10 API Key 与 Provider 管理

Settings 负责管理 LLM Provider 访问能力。

需要支持：

- 创建、查看、删除 API Key。
- 服务端加密存储 key。
- 前端只展示掩码 key。
- 将 key 与 Provider 关联。
- 展示 active/inactive、permission、created time、last used、usage count。
- 测试 Provider 连通性。
- 模型列表不可探测时允许手动录入模型。

Provider 类型：

- 官方 API Provider。
- OpenAI-compatible Relay Provider。
- 自定义 Provider。

验收标准：

- 用户至少能通过 UI 配置一个 Provider，而不需要改代码。
- Provider 测试失败时说明是鉴权、网络、模型不支持、限流还是未知错误。
- 第三方中转站支持不依赖网站 UI 自动化。

## 7. LLM Provider 需求

### 7.1 Provider 抽象

AgentForge 内部逻辑必须依赖统一的 Provider 接口：

- Chat completion request。
- Streaming chat response。
- Tool calling request/response。
- Model capability metadata。
- Usage metadata。
- Normalized error object。

Provider Adapter 负责把统一请求映射到不同供应商 API。

### 7.2 首批官方 API 兼容目标

目标兼容：

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

每个官方 Adapter 需要记录：

- Base URL。
- 鉴权方式。
- Chat endpoint 或 SDK 方法。
- Streaming 支持情况。
- Tool calling 支持情况。
- Model listing 支持情况。
- 已知不支持功能。

### 7.3 第三方中转站兼容目标

AgentForge 必须支持 OpenAI-compatible 中转站：

- OpenRouter。
- One API / New API。
- LiteLLM Proxy。
- 自定义 OpenAI-compatible Base URL。

Relay Provider 配置需要支持：

- Display name。
- Base URL。
- API key。
- 可选 organization/project header。
- Model ID。
- Default model。
- Capability flags。
- Timeout 和 retry policy。
- Streaming 开关。
- Tool calling 开关。

### 7.4 Provider 能力标记

不同 Provider 不一定支持同样能力，所以必须声明 capability flags。

最小能力集合：

- `chat`：标准聊天请求。
- `streaming`：流式响应。
- `tool_calling`：工具或 function call。
- `json_mode`：JSON 或结构化输出。
- `vision`：图像输入。
- `embeddings`：向量嵌入。
- `model_listing`：模型列表。
- `usage_reporting`：token 或费用用量。

除非 Provider 配置或 Adapter 明确声明支持，否则 AgentForge 不得假设能力存在。

## 8. 数据需求

当前持久化实体：

- User。
- Task。
- Step。
- AgentState。
- Memory。
- APIKey。

重构目标可新增：

- ProviderConfig：保存 Provider 级配置和默认 capability JSON。
- ModelConfig：保存模型级配置和 `supports_*` 能力字段。
- ProviderHealthCheck：保存 Provider 最近一次连通性和健康检查结果。

ProviderCapability 不作为独立实体进入当前目标模型。Capability 统一通过 `ProviderConfig.capabilities` 和 `ModelConfig.supports_*` 表达，避免同一能力同时出现在多个权威来源。

数据兼容要求：

- 保留现有 Task、Step、Memory、User、APIKey 数据。
- schema 变更必须使用 Alembic。
- 迁移脚本尽量可回滚。
- 不得静默删除本地 SQLite 开发数据。

## 9. 安全需求

- API Key 必须加密存储。
- 明文 API Key 只能出现在创建或更新请求处理过程中，且不得写入日志。
- 掩码格式需要稳定。
- 生产环境必须要求 JWT secret 和 encryption key。
- Provider test 错误不得泄露 key。
- 前端不得持久化 provider secret，JWT 登录状态除外。

## 10. 成功标准

产品成功：

- 开发者可以配置 Provider、创建 Task、观察 Execution、查看结果，全程不需要改代码。
- Task 失败时给出可行动错误。
- Task、Execution、Step、Agent、Planner、Memory 的区别在 UI 和文档中清晰。

技术成功：

- Provider 逻辑基于 Adapter，不再散落硬编码。
- 当前 `/api/v1` 行为保持兼容，除非明确记录迁移。
- 后端和前端测试覆盖核心 Task 执行与 Provider 配置路径。

文档成功：

- PRD、DESIGN、TECH、SPEC、AGENTS 的范围和术语一致。
- Future Scope 与当前范围明确分离。
- 不把 AgentForge 描述为电商、团队工作区或 Knowledge Base 产品。
