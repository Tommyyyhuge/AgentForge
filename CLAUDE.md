# Claude / Codex 指令

`AGENTS.md` 是本仓库的权威开发规范。修改代码或文档前，先阅读并遵守 `AGENTS.md`。

重要提醒：

- AgentForge 是面向个人开发者的单租户、多智能体 Task 执行与可观测平台。
- 行为变化时保持 PRD、DESIGN、TECH、SPEC、AGENTS 同步。
- 当旧 implementation plans 与新文档冲突时，不要把旧文档当作当前权威。
- LLM Provider 只集成官方 API 和 OpenAI-compatible 中转站，不做供应商网页 UI 自动化。
- 保留工作区中已有的用户改动，不要擅自回退。
- 按变更类型运行对应验证命令，并说明跳过的检查。
