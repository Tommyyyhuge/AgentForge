"""
记忆搜索工具测试

测试 MemorySearchTool 的 Memory Retrieval 检索、降级、结果格式化等功能。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_forge.core.rag_system import DocumentChunk
from agent_forge.tools.memory_search import MemorySearchTool


def _make_chunk(doc_id: str, content: str, chunk_id: str = "chunk_0", index: int = 0):
    """辅助创建 DocumentChunk 对象"""
    return DocumentChunk(
        id=chunk_id,
        doc_id=doc_id,
        content=content,
        index=index,
    )


class TestMemorySearchTool:
    """测试记忆搜索工具"""

    def test_schema_uses_memory_retrieval_language(self):
        """工具 schema 应把检索描述为 Memory Retrieval 而非 Knowledge Base。"""
        tool = MemorySearchTool(rag_system=None)
        schema_text = str(tool.get_schema())

        assert "Memory Retrieval" in schema_text
        assert "Knowledge Base" not in schema_text
        assert "knowledge_base" not in schema_text
        assert "知识库" not in schema_text
        assert "RAG" not in schema_text

    @pytest.mark.asyncio
    async def test_search_with_mock_data(self):
        """测试使用 Mock RAGSystem 搜索"""
        chunk1 = _make_chunk(
            doc_id="doc1",
            content="Python 异步编程使用 async/await 关键字。",
            chunk_id="doc1:chunk_0",
        )
        chunk2 = _make_chunk(
            doc_id="doc2",
            content="AgentForge 使用 FastAPI 构建后端服务。",
            chunk_id="doc2:chunk_0",
        )

        rag_mock = AsyncMock()
        rag_mock.retrieve = AsyncMock(return_value=[chunk1, chunk2])
        rag_mock.get_document = MagicMock(return_value=None)

        tool = MemorySearchTool(rag_system=rag_mock)
        result = await tool.execute(query="异步编程", limit=5)

        assert "Python 异步编程" in result
        assert "AgentForge" in result
        assert "2 条相关结果" in result or "结果" in result
        rag_mock.retrieve.assert_awaited_once_with(query="异步编程", limit=5)

    @pytest.mark.asyncio
    async def test_search_without_rag(self):
        """测试无检索后端时的降级提示"""
        tool = MemorySearchTool(rag_system=None)
        result = await tool.execute(query="测试查询", limit=5)

        assert "未初始化" in result or "未配置" in result
        assert "Memory Retrieval" in result
        assert "RAG" not in result
        assert "Knowledge Base" not in result
        assert "知识库" not in result

    @pytest.mark.asyncio
    async def test_search_result_formatting(self):
        """测试搜索结果格式化输出"""
        chunk = _make_chunk(
            doc_id="doc1",
            content="关键配置信息。",
            chunk_id="doc1:chunk_0",
        )

        rag_mock = AsyncMock()
        rag_mock.retrieve = AsyncMock(return_value=[chunk])
        rag_mock.get_document = MagicMock(return_value=None)

        tool = MemorySearchTool(rag_system=rag_mock)
        result = await tool.execute(query="配置", limit=1)

        # 结果应包含格式化标记
        assert "[记忆搜索结果]" in result
        assert "结果 1" in result or "配置" in result

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """测试空查询处理"""
        tool = MemorySearchTool(rag_system=AsyncMock())
        result = await tool.execute(query="")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """测试搜索无结果时的提示"""
        rag_mock = AsyncMock()
        rag_mock.retrieve = AsyncMock(return_value=[])

        tool = MemorySearchTool(rag_system=rag_mock)
        result = await tool.execute(query="不存在的查询", limit=5)

        assert "未找到" in result or "无结果" in result or "相关" in result

    @pytest.mark.asyncio
    async def test_search_rag_error(self):
        """测试 RAG 检索异常处理"""
        rag_mock = AsyncMock()
        rag_mock.retrieve = AsyncMock(side_effect=RuntimeError("检索服务异常"))

        tool = MemorySearchTool(rag_system=rag_mock)
        result = await tool.execute(query="测试", limit=5)

        assert "错误" in result
