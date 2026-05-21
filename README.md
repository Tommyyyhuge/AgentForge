# AgentForge

> 企业级多智能体协作任务执行平台

## 项目简介

AgentForge 是一个覆盖 8 个核心 AI 方向的多智能体协作平台：

- **ReAct** - 手写推理+行动循环引擎
- **Plan-and-Solve** - 任务规划+依赖图执行
- **Reflection** - 自我反思+经验学习
- **Multi-Agent** - 6 角色协作调度
- **MCP** - 工具注册协议
- **A2A** - Agent 间通信协议
- **RAG** - 向量检索增强
- **Memory** - 三层记忆系统

## 技术栈

### 后端
- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy + PostgreSQL/SQLite
- ChromaDB（向量数据库）
- JWT + bcrypt（认证）

### 前端
- React 18 + TypeScript
- Vite + Tailwind CSS
- Zustand（状态管理）
- Chart.js（数据可视化）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourname/agentforge.git
cd agentforge
```

### 2. 配置 Anaconda 环境

```bash
# 创建虚拟环境（Python 3.11）
conda create -n agentforge python=3.11 -y

# 激活环境
conda activate agentforge

# 验证环境
python --version  # 应显示 Python 3.11.x
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置必要的 API Keys
```

### 5. 启动后端

```bash
# 开发模式
uvicorn main:app --reload

# 生产模式
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 6. 启动前端

```bash
cd frontend
npm install
npm run dev
```

### 7. Docker 一键启动

```bash
# 本地开发
docker-compose up

# 生产部署
./scripts/deploy.sh production
```

## 项目结构

```
AgentForge/
├── backend/              # 后端代码
│   ├── agent_forge/      # 主包
│   │   ├── core/         # 核心引擎
│   │   ├── agents/       # Agent 角色
│   │   ├── tools/        # MCP 工具
│   │   ├── models/       # 数据模型
│   │   ├── api/          # API 路由
│   │   └── ...
│   ├── tests/            # 测试
│   └── requirements.txt  # 依赖
├── frontend/             # 前端代码
│   ├── src/              # 源码
│   └── package.json      # 依赖
├── docs/                 # 文档
├── scripts/              # 脚本
└── docker-compose.yml    # Docker 配置
```

## 文档

- [设计文档](docs/superpowers/specs/2026-05-19-agentforge-design.md)
- [实现计划](docs/IMPLEMENTATION_PLAN.md)
- [Week 1 任务清单](docs/WEEK1_DETAILED_TASKS.md)
- [Anaconda 配置指南](docs/ANACONDA_SETUP.md)

## 开发规范

### 代码格式

```bash
# 后端
black agent_forge/
isort agent_forge/
mypy agent_forge/

# 前端
npm run lint
npm run format
```

### 测试

```bash
# 后端测试
cd backend
pytest --cov=agent_forge --cov-report=html

# 前端测试
cd frontend
npm test
```

## 面试展示

### 5 分钟快速演示

1. 打开 Web Demo → 专业 Dashboard 界面
2. 选择预设任务场景（调研/编程/写作）
3. 实时观看 Planner 拆解任务 → 依赖图可视化
4. 多 Agent 协作执行 → ReAct 循环可视化
5. 查看反思报告 + 性能监控 Dashboard

## 许可证

MIT License

## 作者

- 开发者: [Your Name]
- 日期: 2026-05-19
