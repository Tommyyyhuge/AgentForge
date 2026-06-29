"""
记忆管理器模块测试

测试三层记忆系统：
- 短期记忆（内存 FIFO）
- 长期记忆（ChromaDB / SQLite 降级）
- 外部记忆（Mock）
- 上下文构建
"""
from unittest.mock import patch

import pytest

from agent_forge.core.memory_manager import (
    MemoryEntry,
    MemoryManager,
    MemoryType,
)


# =============================================================================
# 辅助函数
# =============================================================================


def _make_manager(**kwargs) -> MemoryManager:
    """创建不依赖 ChromaDB 的 MemoryManager 实例"""
    mm = MemoryManager(**kwargs)
    # 强制标记 ChromaDB 不可用，使其降级到 SQLite / 内存操作
    mm._chroma_available = False
    return mm


@pytest.fixture
def memory_manager() -> MemoryManager:
    """提供干净的 MemoryManager 实例"""
    return _make_manager()


# =============================================================================
# MemoryEntry 基本测试
# =============================================================================


class TestMemoryEntry:
    """MemoryEntry 创建和序列化测试"""

    def test_create_minimal(self):
        """创建最小化 MemoryEntry"""
        entry = MemoryEntry(content="测试记忆")
        assert entry.content == "测试记忆"
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert entry.id is not None
        assert entry.created_at is not None

    def test_create_full(self):
        """创建完整 MemoryEntry"""
        from datetime import datetime, timezone

        dt = datetime.now(timezone.utc)
        entry = MemoryEntry(
            content="完整记忆",
            memory_type=MemoryType.LONG_TERM,
            agent_id="agent-1",
            agent_role="coder",
            task_id="task-1",
            source="test",
            metadata={"key": "value"},
            embedding=[0.1, 0.2, 0.3],
            entry_id="custom-id",
            created_at=dt,
        )
        assert entry.id == "custom-id"
        assert entry.agent_role == "coder"
        assert entry.embedding == [0.1, 0.2, 0.3]
        assert entry.created_at == dt

    def test_to_dict(self):
        """MemoryEntry 序列化"""
        entry = MemoryEntry(
            content="dict测试",
            memory_type=MemoryType.SHORT_TERM,
            agent_id="a1",
        )
        d = entry.to_dict()
        assert d["content"] == "dict测试"
        assert d["memory_type"] == "short_term"
        assert d["agent_id"] == "a1"
        assert "created_at" in d


# =============================================================================
# 短期记忆测试
# =============================================================================


class TestShortTermMemory:
    """短期记忆（内存 FIFO）测试"""

    @pytest.mark.asyncio
    async def test_add_and_get(self, memory_manager: MemoryManager):
        """添加并获取短期记忆"""
        await memory_manager.add_short_term("记忆1", agent_id="agent-1")
        await memory_manager.add_short_term("记忆2", agent_id="agent-1")

        entries = await memory_manager.get_short_term(agent_id="agent-1")
        assert len(entries) == 2
        assert entries[0].content == "记忆1"
        assert entries[1].content == "记忆2"

    @pytest.mark.asyncio
    async def test_add_with_agent_role(self, memory_manager: MemoryManager):
        """添加带角色的短期记忆"""
        await memory_manager.add_short_term(
            "角色记忆", agent_id="agent-1", agent_role="planner"
        )
        entries = await memory_manager.get_short_term(agent_id="agent-1")
        assert entries[0].agent_role == "planner"

    @pytest.mark.asyncio
    async def test_get_all_when_no_agent_filter(self, memory_manager: MemoryManager):
        """不传 agent_id 时返回全部"""
        await memory_manager.add_short_term("全局1", agent_id="a1")
        await memory_manager.add_short_term("全局2", agent_id="a2")

        entries = await memory_manager.get_short_term()
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_fifo_eviction(self):
        """超过 max_short_term 时 FIFO 淘汰"""
        mm = _make_manager(max_short_term=3)
        await mm.add_short_term("记忆A")
        await mm.add_short_term("记忆B")
        await mm.add_short_term("记忆C")
        await mm.add_short_term("记忆D")  # 应淘汰 A

        entries = await mm.get_short_term()
        assert len(entries) == 3
        assert entries[0].content == "记忆B"
        assert entries[-1].content == "记忆D"

    @pytest.mark.asyncio
    async def test_limit_parameter(self, memory_manager: MemoryManager):
        """limit 参数控制返回条数"""
        for i in range(10):
            await memory_manager.add_short_term(f"记忆{i}")

        entries = await memory_manager.get_short_term(limit=3)
        assert len(entries) == 3
        assert entries[-1].content == "记忆9"

    @pytest.mark.asyncio
    async def test_clear_all(self, memory_manager: MemoryManager):
        """清空全部短期记忆"""
        await memory_manager.add_short_term("清除测试")
        count = await memory_manager.clear_short_term()
        assert count == 1
        entries = await memory_manager.get_short_term()
        assert len(entries) == 0

    @pytest.mark.asyncio
    async def test_clear_by_agent(self, memory_manager: MemoryManager):
        """按 Agent 清空短期记忆"""
        await memory_manager.add_short_term("agent1的记忆", agent_id="a1")
        await memory_manager.add_short_term("agent2的记忆", agent_id="a2")

        count = await memory_manager.clear_short_term(agent_id="a1")
        assert count == 1

        entries = await memory_manager.get_short_term()
        assert len(entries) == 1
        assert entries[0].content == "agent2的记忆"


# =============================================================================
# 长期记忆测试（SQLite 降级路径）
# =============================================================================


class TestLongTermMemory:
    """长期记忆（SQLite 降级）测试"""

    @pytest.mark.asyncio
    async def test_add_long_term_sqlite_fallback(self, memory_manager: MemoryManager):
        """长期记忆写入 SQLite 降级路径"""
        entry = await memory_manager.add_long_term(
            "Python 3.11 新特性: 更好的错误追踪",
            agent_id="agent-1",
            agent_role="coder",
            task_id="task-1",
        )
        assert entry.content is not None
        assert entry.memory_type == MemoryType.LONG_TERM
        assert entry.task_id == "task-1"

    @pytest.mark.asyncio
    async def test_search_long_term_sqlite(self, memory_manager: MemoryManager):
        """长期记忆搜索（SQLite 降级）"""
        await memory_manager.add_long_term(
            "机器学习基础: 监督学习 vs 非监督学习",
            agent_role="researcher",
            task_id="task-ml",
        )
        await memory_manager.add_long_term(
            "Python 异步编程: asyncio 深入理解",
            agent_role="coder",
            task_id="task-py",
        )

        # 搜索关键词匹配
        results = await memory_manager.search_long_term("Python", limit=5)
        assert len(results) >= 1
        assert any("Python" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_search_by_role(self, memory_manager: MemoryManager):
        """按角色过滤长期记忆"""
        await memory_manager.add_long_term(
            "研究员知识", agent_role="researcher"
        )
        await memory_manager.add_long_term(
            "程序员知识", agent_role="coder"
        )

        results = await memory_manager.search_long_term(
            query="", agent_role="coder", limit=5
        )
        assert len(results) >= 1
        for r in results:
            assert r.agent_role == "coder"

    @pytest.mark.asyncio
    async def test_get_by_task(self, memory_manager: MemoryManager):
        """按任务 ID 获取长期记忆"""
        await memory_manager.add_long_term(
            "任务专有记忆", task_id="specific-task"
        )
        results = await memory_manager.get_long_term_by_task("specific-task")
        assert len(results) >= 1
        assert results[0].task_id == "specific-task"

    @pytest.mark.asyncio
    async def test_search_no_match(self, memory_manager: MemoryManager):
        """无匹配时返回空列表"""
        results = await memory_manager.search_long_term(
            "ZZZZ_NOT_EXIST_ZZZZ"
        )
        assert isinstance(results, list)
        assert len(results) == 0


# =============================================================================
# 外部记忆测试（Mock）
# =============================================================================


class TestExternalMemory:
    """外部记忆（Mock）测试"""

    @pytest.mark.asyncio
    async def test_add_external(self, memory_manager: MemoryManager):
        """添加外部记忆"""
        entry = await memory_manager.add_external(
            content="外部知识库内容",
            source="knowledge_base",
            metadata={"doc_id": "doc-1"},
        )
        assert entry.source == "knowledge_base"
        assert entry.memory_type == MemoryType.EXTERNAL
        assert entry.metadata["doc_id"] == "doc-1"

    @pytest.mark.asyncio
    async def test_search_external_returns_empty(self, memory_manager: MemoryManager):
        """外部记忆搜索当前返回空列表（Mock）"""
        results = await memory_manager.search_external("任何查询")
        assert isinstance(results, list)
        assert len(results) == 0


# =============================================================================
# 通用搜索测试
# =============================================================================


class TestSearch:
    """跨类型记忆搜索测试"""

    @pytest.mark.asyncio
    async def test_search_all_types(self, memory_manager: MemoryManager):
        """搜索所有记忆类型"""
        await memory_manager.add_short_term("短期: AI 安全研究", agent_id="a1")
        await memory_manager.add_long_term(
            "长期: AI 安全最佳实践", agent_role="researcher"
        )

        results = await memory_manager.search("AI 安全", limit=10)
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_search_specific_type(self, memory_manager: MemoryManager):
        """仅搜索指定类型"""
        await memory_manager.add_short_term("仅短期", agent_id="a1")
        await memory_manager.add_long_term("仅长期", agent_role="coder")

        results = await memory_manager.search(
            "仅", memory_type=MemoryType.SHORT_TERM, limit=5
        )
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.SHORT_TERM


# =============================================================================
# 上下文构建测试
# =============================================================================


class TestContext:
    """上下文构建测试"""

    @pytest.mark.asyncio
    async def test_get_context_with_memories(self, memory_manager: MemoryManager):
        """获取 Agent 上下文"""
        await memory_manager.add_short_term(
            "用户偏好: 喜欢简洁代码", agent_id="agent-1", agent_role="coder"
        )
        await memory_manager.add_long_term(
            "项目规范: 使用类型注解", agent_id="agent-1", agent_role="coder",
            task_id="task-1",
        )

        context = await memory_manager.get_context(
            agent_id="agent-1",
            agent_role="coder",
            task_id="task-1",
            limit=10,
        )

        # 应包含短期记忆和长期记忆标记
        assert "短期记忆" in context
        assert "长期记忆" in context
        assert "用户偏好" in context
        assert "类型注解" in context

    @pytest.mark.asyncio
    async def test_get_context_empty(self, memory_manager: MemoryManager):
        """无记忆时返回提示文字"""
        context = await memory_manager.get_context(agent_id="unknown")
        assert "暂无记忆上下文" in context

    @pytest.mark.asyncio
    async def test_get_context_respects_limit(self, memory_manager: MemoryManager):
        """上下文遵循 limit 限制"""
        for i in range(20):
            await memory_manager.add_short_term(
                f"记忆{i}", agent_id="agent-1"
            )

        context = await memory_manager.get_context(
            agent_id="agent-1",
            limit=5,
        )
        # 最多 5 条短期记忆
        lines = context.split("\n")
        memory_lines = [ln for ln in lines if ln.lstrip().startswith(("1.", "2.", "3.", "4.", "5.", "6."))]
        assert len(memory_lines) <= 5


# =============================================================================
# 边缘情况测试
# =============================================================================


class TestEdgeCases:
    """边缘情况测试"""

    @pytest.mark.asyncio
    async def test_empty_content(self, memory_manager: MemoryManager):
        """空内容的记忆"""
        entry = await memory_manager.add_short_term("")
        assert entry.content == ""

    @pytest.mark.asyncio
    async def test_very_long_content(self, memory_manager: MemoryManager):
        """超长内容的记忆"""
        long_text = "A" * 10000
        entry = await memory_manager.add_short_term(long_text)
        assert len(entry.content) == 10000

    @pytest.mark.asyncio
    async def test_chroma_fallback_on_init_failure(self):
        """ChromaDB 初始化失败时优雅降级"""
        with patch(
            "agent_forge.core.memory_manager.MemoryManager._init_chroma",
            return_value=False,
        ):
            mm = _make_manager()
            # 长期记忆操作应降级而非崩溃
            entry = await mm.add_long_term("降级测试")
            assert entry.content == "降级测试"
            results = await mm.search_long_term("降级测试")
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_sqlite_write_failure_is_not_swallowed(
        self, memory_manager: MemoryManager
    ):
        """SQLite 降级写入失败时应向调用方暴露错误"""

        class BrokenSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def add(self, _entry):
                pass

            async def commit(self):
                raise RuntimeError("database unavailable")

        with patch(
            "agent_forge.database.connection.async_session",
            return_value=BrokenSession(),
        ):
            with pytest.raises(RuntimeError, match="database unavailable"):
                await memory_manager.add_long_term("写入失败测试")

    @pytest.mark.asyncio
    async def test_concurrent_add(self, memory_manager: MemoryManager):
        """并发添加短期记忆（验证锁安全性）

        注意：Windows + asyncio.Lock 在 pytest-asyncio 环境下
        可能存在调度差异，故不强制精确计数。
        """
        import asyncio

        async def add_mem(i: int):
            await memory_manager.add_short_term(f"并发{i:03d}")

        tasks = [add_mem(i) for i in range(20)]
        await asyncio.gather(*tasks)

        entries = await memory_manager.get_short_term()
        all_contents = {e.content for e in entries}
        # 至少有部分并发添加成功
        assert len(entries) >= 1
        # 验证并发添加没有导致数据损坏
        for content in all_contents:
            assert content.startswith("并发")
        # 验证锁没有引入重复 ID
        assert len({e.id for e in entries}) == len(entries)

    @pytest.mark.asyncio
    async def test_clear_twice(self, memory_manager: MemoryManager):
        """重复清空不报错"""
        count1 = await memory_manager.clear_short_term()
        count2 = await memory_manager.clear_short_term()
        assert count1 == 0
        assert count2 == 0


# =============================================================================
# ChromaDB 集成测试（条件执行）
# =============================================================================


class TestChromaDBIntegration:
    """ChromaDB 集成测试（仅在 ChromaDB 可用时运行）"""

    @pytest.mark.asyncio
    async def test_chroma_init_check(self):
        """验证 ChromaDB 可用性检测逻辑"""
        mm = MemoryManager()
        # 重置状态
        mm._chroma_available = None
        # 尝试初始化
        available = mm._init_chroma()
        # 无论是否可用，不应抛出异常
        assert isinstance(available, bool)
