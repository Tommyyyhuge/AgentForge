# AgentForge Agent 开发规范

## 1. 权威来源

以下文件是当前项目规则的权威来源：

- `docs/PRD.md`：产品范围、领域语言、当前能力与未来范围。
- `docs/DESIGN.md`：UI、布局、设计 token、页面职责。
- `docs/TECH.md`：架构、API、数据、Provider、测试、部署。
- `docs/SPEC.md`：实施 issue 清单和建议顺序。
- `AGENTS.md`：开发流程和质量规则。

`docs/IMPLEMENTATION_PLAN*.md` 和 `docs/superpowers/specs/` 下的旧文档只作为历史资料。当旧文档与上述文件冲突时，以上述文件为准。

## 2. 产品规则

- AgentForge 是面向个人开发者的单租户、多智能体 Task 执行与可观测平台。
- 核心用户流程是：创建 Task，Planner 拆解，Agent 执行，用户观察 Step，复盘结果，有价值上下文沉淀为 Memory。
- Planner 是组件，不是内置可执行 Agent。
- 内置可执行 Agent role 是 Researcher、Coder、Writer、Reviewer、Executor。
- Memory 是 Agent 可复用的执行上下文，不要称为 Knowledge Base。
- Knowledge Base、团队工作区、管理员角色、插件市场、PWA、国际化、完整多次运行历史属于 Future Scope。
- LLM 集成使用官方 API 和 OpenAI-compatible 中转站，不实现供应商网页 UI 自动化。

## 3. 术语规范

统一使用：

- AgentForge。
- User。
- Task。
- Planner。
- Agent。
- Execution。
- Step。
- Memory。
- Memory Retrieval。
- Provider。
- Provider Adapter。
- Relay Provider。
- API Key。

当前范围避免使用：

- Workspace。
- Organization。
- Administrator role。
- Knowledge Base。
- Pipeline。
- Job。
- Ticket。
- Website automation。

## 4. 仓库边界

后端：

- `backend/agent_forge/api`：routes、middleware、response shaping。
- `backend/agent_forge/models`：Pydantic schemas 和 API models。
- `backend/agent_forge/database`：ORM models 和数据库连接。
- `backend/agent_forge/core`：orchestration、Planner、Execution、Memory、metrics、Provider services。
- `backend/agent_forge/agents`：内置 Agent 实现。
- `backend/agent_forge/tools`：内置工具。
- `backend/alembic`：数据库迁移。
- `backend/tests`：后端测试。

前端：

- `frontend/src/api`：HTTP/SSE client 和 response parsing。
- `frontend/src/types`：前端领域类型和 API 类型。
- `frontend/src/stores`：Zustand store 和 API orchestration。
- `frontend/src/pages`：路由页面。
- `frontend/src/components`：UI、layout、charts、flow 组件。
- `frontend/src/hooks`：hooks。
- `frontend/tests`：前端测试。

文档：

- 行为变化时同步维护 `docs/PRD.md`、`docs/DESIGN.md`、`docs/TECH.md`、`docs/SPEC.md`。

## 5. 后端开发规则

- FastAPI route handler 保持薄。
- 业务逻辑放在 `core`、`agents` 或专门 service 中。
- 不直接把 ORM object 作为 API contract 返回。
- Route request/response 使用 Pydantic schema。
- 保持 `/api/v1` 兼容性，除非明确记录迁移。
- schema 变更使用 Alembic。
- 保留 SQLite 本地开发和 PostgreSQL 部署支持。
- embedded Chroma 是当前 Memory 存储方案，除非新 ADR 修改。
- 不记录明文 API Key。
- 不在 metrics 中持久化敏感 prompt 内容。
- Provider error 返回前必须归一化。

## 6. 前端开发规则

- API response parsing 放在 `api` 或 store mapping 中。
- 展示组件接收 typed props，不依赖原始 backend payload。
- 遵循现有 Tailwind 和组件模式，除非 DESIGN.md 要求调整。
- Task、Agent、Provider、Step 状态使用语义状态色。
- 避免卡片嵌套卡片。
- 保持深色技术控制台风格。
- 用户可见的异步流程需要 loading、empty、error、degraded 状态。
- 组件卸载时关闭 EventSource/SSE。
- 纯图标按钮需要 accessible label。

## 7. Provider 开发规则

- Provider-specific 代码必须在 Provider Adapter 后面。
- Execution、Agent、Planner 代码使用统一 Provider interface。
- 官方 Provider 和 Relay Provider 必须声明 capability flags。
- 不得默认假设 streaming、tool calling、JSON mode、vision、embeddings、model listing、usage reporting 可用。
- 第三方中转站优先按 OpenAI-compatible 支持。
- 非 OpenAI-compatible 中转站需要单独 Adapter。
- Provider test result 必须用户安全，不泄露 secret。

## 8. 测试规则

后端按变更类型验证：

- 纯文档：无需后端测试，除非文档声称生成了行为。
- 后端逻辑：运行 `python -m pytest`。
- 后端类型敏感变更：运行 `python -m mypy agent_forge --ignore-missing-imports`。
- 后端风格敏感变更：运行 `python -m flake8 agent_forge`。
- migration 变更：尽量验证 SQLite 和 PostgreSQL 假设。

前端按变更类型验证：

- 前端逻辑或组件：运行 `npm run test`。
- lint 敏感变更：运行 `npm run lint`。
- build/type 变更：运行 `npm run build`。

完整验证目标：

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

## 9. 文档同步规则

行为变化时更新：

- 产品范围或用户流程变化：更新 `docs/PRD.md`。
- UI、导航、视觉、交互变化：更新 `docs/DESIGN.md`。
- API、架构、数据、Provider、部署、质量门禁变化：更新 `docs/TECH.md`。
- 实施 issue 范围或顺序变化：更新 `docs/SPEC.md`。
- 开发流程变化：更新 `AGENTS.md`。
- `CLAUDE.md` 保持简短，只指向 `AGENTS.md`。

## 10. 变更纪律

- 变更范围保持在用户请求内。
- 不重构无关模块。
- 不回退用户已有改动。
- 工作区有未提交改动时，保留无关改动。
- 优先使用项目现有模式。
- 只有在确实减少重复或隔离清晰边界时才增加抽象。
- 没有明确理由和文档更新，不新增依赖。
- 永远不提交 secret。

## 11. Commit 和 PR 期望

- 总结产品影响和技术影响。
- 列出已运行的验证命令。
- 说明跳过的测试和原因。
- 标明 migration 或兼容性变化。
- 标明文档更新。
