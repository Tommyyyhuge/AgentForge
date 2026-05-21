"""
AgentForge API 路由模块
"""
from agent_forge.api.routes.tasks import router as tasks_router
from agent_forge.api.routes.agents import router as agents_router
from agent_forge.api.routes.auth import router as auth_router

__all__ = ["tasks_router", "agents_router", "auth_router"]
