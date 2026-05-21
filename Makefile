# AgentForge Makefile

.PHONY: help install dev-install test lint format clean docker-build docker-up docker-down

# 默认目标
help:
	@echo "AgentForge 开发命令"
	@echo ""
	@echo "后端命令:"
	@echo "  make install       安装后端依赖"
	@echo "  make dev-install   安装开发依赖"
	@echo "  make test          运行后端测试"
	@echo "  make lint          代码检查"
	@echo "  make format        代码格式化"
	@echo "  make run           启动后端服务"
	@echo ""
	@echo "前端命令:"
	@echo "  make install-frontend  安装前端依赖"
	@echo "  make run-frontend      启动前端服务"
	@echo ""
	@echo "Docker 命令:"
	@echo "  make docker-build  构建 Docker 镜像"
	@echo "  make docker-up     启动 Docker 服务"
	@echo "  make docker-down   停止 Docker 服务"
	@echo ""
	@echo "其他命令:"
	@echo "  make clean         清理缓存文件"
	@echo "  make check         运行所有检查"

# 后端命令
install:
	cd backend && pip install -r requirements.txt

dev-install:
	cd backend && pip install -r requirements.txt
	cd backend && pip install -r requirements-dev.txt

test:
	cd backend && pytest --cov=agent_forge --cov-report=html

test-unit:
	cd backend && pytest tests/unit -v

test-integration:
	cd backend && pytest tests/integration -v

lint:
	cd backend && flake8 agent_forge/
	cd backend && mypy agent_forge/

format:
	cd backend && black agent_forge/
	cd backend && isort agent_forge/

run:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-prod:
	cd backend && gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 前端命令
install-frontend:
	cd frontend && npm install

run-frontend:
	cd frontend && npm run dev

build-frontend:
	cd frontend && npm run build

# Docker 命令
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# 其他命令
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

check:
	make format
	make lint
	make test
	@echo "✅ 所有检查通过"

# 初始化项目
init:
	conda create -n agentforge python=3.11 -y
	@echo "请运行: conda activate agentforge"
	@echo "然后运行: make install"
