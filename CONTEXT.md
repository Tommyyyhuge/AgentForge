# AgentForge Context

AgentForge is a single-tenant, lightly authenticated multi-agent task execution and observability platform. It exists to let a user create tasks, route work through specialized agents, inspect progress, and preserve useful task memory.

## Language

**AgentForge**:
The product context for orchestrating AI agents to complete user-requested tasks.
_Avoid_: enterprise collaboration platform, team workspace platform

**Task**:
A user-requested unit of work that can be planned, executed, observed, and reviewed.
_Avoid_: project, ticket, job

**Agent**:
A specialized AI worker that contributes a role-specific part of a task.
_Avoid_: bot, assistant, service

**Planner**:
The planning component that breaks a task into agent-assignable work.
_Avoid_: planner agent, planning agent

**Execution**:
The lifecycle of turning a task into agent actions and results, not a standalone run record.
_Avoid_: workflow, pipeline, run

**Memory**:
Persisted task context that can be reused by agents across executions.
_Avoid_: knowledge base, document store

**Memory Retrieval**:
The mechanism agents use to find relevant persisted memory during an execution.
_Avoid_: standalone RAG product, document question answering

**Knowledge Base**:
A user-managed collection of explicit source material for agents to consult.
_Avoid_: memory, agent memory

**User**:
The authenticated person operating AgentForge in a single-tenant environment.
_Avoid_: admin, team member, workspace member

**API Key**:
A credential used to authorize programmatic access with a scoped permission level.
_Avoid_: admin user, service account

**Future Scope**:
Capabilities that are intentionally outside the current product boundary.
_Avoid_: current feature, implemented capability

## Relationships

- A **User** creates one or more **Tasks**.
- A **Planner** decomposes a **Task** before **Agents** execute the planned work.
- A **Task** has one **Execution** lifecycle; repeated run history is **Future Scope**.
- An **Execution** may involve one or more **Agents**.
- An **Agent** may read from or write to **Memory** during an **Execution**.
- **Memory Retrieval** supports **Memory** reuse and should not be described as a separate product capability.
- A **Knowledge Base** is **Future Scope** and should not be described as the current **Memory** capability.
- An **API Key** may have elevated permissions, but those permissions do not make the **User** an administrator.
- **Future Scope** includes team workspaces, administrator roles, organization-level permissions, plugin marketplaces, PWA support, internationalization, and user-managed knowledge bases.

## Example dialogue

> **Dev:** "Should this release include workspace administrators and team permissions?"
> **Domain expert:** "No. AgentForge currently has a **User** in a single-tenant context. Administrator roles and team permissions are **Future Scope**."
>
> **Dev:** "Should we create a separate Execution object for every task run?"
> **Domain expert:** "No. For now, **Execution** describes the lifecycle of a **Task**. Separate run records only become relevant when repeated run history enters scope."
>
> **Dev:** "Do we have six Agents if the planner assigns work?"
> **Domain expert:** "No. The **Planner** prepares work for **Agents**; it is not itself an **Agent**."
>
> **Dev:** "Can we call the current memory system a knowledge base?"
> **Domain expert:** "No. **Memory** is task context produced and reused during executions; a **Knowledge Base** is user-managed source material and remains **Future Scope**."
>
> **Dev:** "Should RAG be listed as its own product capability?"
> **Domain expert:** "No. In the current scope, retrieval belongs under **Memory Retrieval**; it does not imply a full document question-answering product."
>
> **Dev:** "If an API key has admin permission, does that mean the user is an administrator?"
> **Domain expert:** "No. **API Key** permissions authorize programmatic access; administrator **User** roles remain **Future Scope**."

## Flagged ambiguities

- "Enterprise platform" was used in earlier documentation to describe capabilities that are not currently implemented. Resolved: AgentForge is currently a single-tenant multi-agent task execution and observability platform.
- "Admin account" was used during setup, but the current domain has only **User** accounts. Resolved: administrator roles are **Future Scope** unless the domain model is expanded.
- "ChromaDB service" appears in older documentation, but the current product boundary should describe **Memory** rather than committing domain language to a specific storage topology.
- "Execution" can mean either a task lifecycle or a separate run record. Resolved: it means a **Task** lifecycle; separate run records are **Future Scope**.
- "Planner" was previously counted as an agent role. Resolved: **Planner** is a planning component, while **Agent** means a worker that executes planned work.
- "Memory" and "Knowledge Base" were previously easy to conflate. Resolved: **Memory** is current agent/task context; **Knowledge Base** is **Future Scope**.
- "RAG" was previously easy to read as a standalone product capability. Resolved: retrieval is part of **Memory Retrieval**, not a separate knowledge-base feature.
- "admin" can refer to an API key permission or a user role. Resolved: current scope supports **API Key** permissions only; administrator **User** roles are **Future Scope**.
