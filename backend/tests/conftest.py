"""
AgentForge 测试配置
"""
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from agent_forge.database.connection import async_session, close_db, init_db


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """测试数据库初始化"""
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    """数据库会话"""
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(autouse=True)
def reset_agent_factory():
    """重置 AgentFactory 注册表，确保每次测试前所有 Agent 已注册"""
    from agent_forge.agents.factory import AgentFactory
    from agent_forge.agents.executor_agent import ExecutorAgent
    from agent_forge.agents.researcher_agent import ResearcherAgent
    from agent_forge.agents.coder_agent import CoderAgent
    from agent_forge.agents.writer_agent import WriterAgent
    from agent_forge.agents.reviewer_agent import ReviewerAgent
    from agent_forge.models.schemas import AgentRole

    # 清空并重新注册所有 Agent
    AgentFactory._registry.clear()
    AgentFactory.register(AgentRole.EXECUTOR, ExecutorAgent)
    AgentFactory.register(AgentRole.RESEARCHER, ResearcherAgent)
    AgentFactory.register(AgentRole.CODER, CoderAgent)
    AgentFactory.register(AgentRole.WRITER, WriterAgent)
    AgentFactory.register(AgentRole.REVIEWER, ReviewerAgent)
    yield
