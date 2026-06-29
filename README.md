# AgentForge

> Single-tenant, lightly authenticated multi-agent task execution and observability platform.

AgentForge lets a user create tasks, route work through a planner and specialized agents, inspect execution progress, and preserve useful task memory. The current product boundary is intentionally smaller than a team workspace product; see [AGENTS.md](./AGENTS.md), [docs/PRD.md](./docs/PRD.md), [docs/TECH.md](./docs/TECH.md), [docs/SPEC.md](./docs/SPEC.md), and [docs/DESIGN.md](./docs/DESIGN.md) for the authoritative product, technical, implementation, design, and development rules.

## Current Scope

AgentForge currently includes:

- Task creation, execution, inspection, and review.
- A **Planner** that decomposes a task before agent execution.
- Five built-in executable **Agents**: Researcher, Coder, Writer, Reviewer, and Executor.
- ReAct-style execution loops, reflection support, agent-to-agent messaging, and MCP-style tool registration.
- **Memory** and **Memory Retrieval** for reusable task context.
- Lightweight user authentication, API keys, metrics, and a React dashboard.

Not current scope:

- Administrator user roles or team permissions.
- Workspaces, organizations, or multi-tenant collaboration.
- Plugin marketplace, PWA support, or internationalization.
- A user-managed **Knowledge Base** or full document question-answering product.

## Architecture

Docker Compose runs four services:

```text
Browser
  |
  v
Frontend: React 19 + Vite build served by Nginx
  |
  | /api/*
  v
Backend: FastAPI
  |-- PostgreSQL 16 for application data
  |-- Redis 7 for cache/message support
  |-- embedded Chroma persistence for Memory
```

Chroma is not a separate Compose service. The backend uses an embedded Chroma persistent client and mounts `chroma_data` at `/data/chromadb`. The decision is recorded in [docs/adr/0001-use-embedded-chroma-for-memory.md](./docs/adr/0001-use-embedded-chroma-for-memory.md).

## Tech Stack

Backend:

- Python 3.11+
- FastAPI, Uvicorn
- SQLAlchemy, Alembic
- PostgreSQL in Docker, SQLite for local development
- ChromaDB embedded persistence with SQLite fallback
- Redis
- JWT, bcrypt, encrypted API keys

Frontend:

- React 19, TypeScript 6
- Vite 8
- Tailwind CSS
- Zustand
- React Router 7
- React Flow
- Recharts
- Axios

## Quick Start With Docker

Prerequisite: Docker Desktop must be running.

From the repository root:

```powershell
$env:JWT_SECRET_KEY='0123456789abcdef0123456789abcdef'
$env:ENCRYPTION_KEY='abcdef0123456789abcdef0123456789'
docker compose up -d --build
```

Open:

- Frontend: <http://localhost:3000>
- Backend API docs: <http://localhost:8000/docs>
- Backend health: <http://localhost:8000/health>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

Useful Docker commands:

```powershell
docker compose ps
docker compose logs -f backend
docker compose down
```

## Local Development

Backend:

```powershell
cd backend
pip install -r requirements.txt
$env:JWT_SECRET_KEY='0123456789abcdef0123456789abcdef'
$env:ENCRYPTION_KEY='abcdef0123456789abcdef0123456789'
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server defaults to <http://localhost:5173>.

## Environment Variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `ENVIRONMENT` | No | `development` | Runtime environment |
| `DB_TYPE` | No | `sqlite` | `sqlite` or `postgresql` |
| `DATABASE_URL` | Depends | `sqlite:///data/agentforge.db` | Required for PostgreSQL deployments |
| `JWT_SECRET_KEY` | Yes | none | JWT signing secret |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_EXPIRE_DAYS` | No | `7` | Token lifetime |
| `ENCRYPTION_KEY` | Yes | none | Secret used for API key encryption |
| `ENCRYPTION_SALT` | No | `agentforge-salt` | PBKDF2 salt |
| `KIMI_API_KEY` | No | none | Optional Moonshot/Kimi key |
| `KIMI_BASE_URL` | No | `https://api.moonshot.cn` | Kimi endpoint |
| `DEEPSEEK_API_KEY` | No | none | Optional DeepSeek key |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek endpoint |
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL |
| `CHROMA_PERSIST_DIR` | No | `./data/chromadb` | Embedded Chroma data directory |
| `ENABLE_MONITORING` | No | `true` | Metrics collection switch |
| `METRICS_RETENTION_DAYS` | No | `30` | Metrics retention window |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `LOG_FORMAT` | No | `json` | Logging format |

## Project Structure

```text
AgentForge/
  backend/
    agent_forge/
      agents/       # executable agent implementations and factory
      api/          # REST routes: tasks, agents, auth, keys, metrics
      config/       # settings
      core/         # planner, execution loop, memory, messaging, LLM routing
      database/     # ORM models, connection, migrations
      mcp/          # tool registry
      tools/        # built-in tools
      utils/        # logging and crypto helpers
    alembic/        # database migrations
    tests/          # backend tests
    main.py         # FastAPI entrypoint
  frontend/
    src/
      api/          # HTTP/SSE clients
      components/   # UI components
      hooks/        # React hooks
      pages/        # app views
      stores/       # Zustand stores
    tests/          # frontend tests
  docs/
    adr/            # architectural decision records
    superpowers/    # design/spec history
  CONTEXT.md        # supplemental project language notes
  docker-compose.yml
  Dockerfile        # backend image
  nginx.conf
```

## Verification

Backend:

```powershell
cd backend
python -m pytest
python -m mypy agent_forge --ignore-missing-imports
python -m flake8 agent_forge
```

Frontend:

```powershell
cd frontend
npm run lint
npm run test
npm run build
```

## Notes

- A regular **User** account is not an administrator role. Administrator user roles are future scope.
- `admin` on an **API Key** is a permission level for programmatic access, not a user role.
- **Memory Retrieval** is part of the current memory system. A user-managed **Knowledge Base** is future scope.

## Documentation

Current authoritative documents:

- [Agent instructions](./AGENTS.md)
- [Product requirements](./docs/PRD.md)
- [Technical architecture](./docs/TECH.md)
- [Refactor issue specification](./docs/SPEC.md)
- [Design guidelines](./docs/DESIGN.md)

Supplemental and historical documents:

- [Project context notes](./CONTEXT.md)
- [Embedded Chroma ADR](./docs/adr/0001-use-embedded-chroma-for-memory.md)
- [Historical implementation plan](./docs/IMPLEMENTATION_PLAN.md)
- [Anaconda setup](./docs/ANACONDA_SETUP.md)

## License

MIT License
