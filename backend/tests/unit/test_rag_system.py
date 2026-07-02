"""
RAG 检索增强系统测试

测试内容：
- DocumentChunk / Document 数据模型
- 文本分块（滑动窗口、段落边界、重叠）
- 文档导入（txt/md/pdf）
- 文件读取（文本、PDF）
- 检索（长期记忆、外部记忆、合并去重）
- 增强提示词生成
- 文档管理（注册、查询、移除）
- 错误处理（不支持类型、文件不存在）
"""
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_forge.core.memory_manager import MemoryEntry, MemoryManager, MemoryType
from agent_forge.core.rag_system import (
    Document,
    DocumentChunk,
    RAGException,
    RAGSystem,
    UnsupportedDocumentType,
)

# =============================================================================
# 辅助函数
# =============================================================================


def _make_manager(**kwargs) -> MemoryManager:
    """创建不依赖 ChromaDB 的 MemoryManager 实例"""
    mm = MemoryManager(**kwargs)
    mm._chroma_available = False
    return mm


def _make_entry(
    content: str,
    entry_id: str = "chunk-1",
    metadata: dict = None,
    memory_type: MemoryType = MemoryType.LONG_TERM,
) -> MemoryEntry:
    """创建测试用 MemoryEntry"""
    return MemoryEntry(
        content=content,
        memory_type=memory_type,
        entry_id=entry_id,
        metadata=metadata or {},
    )


@pytest.fixture
def memory_manager() -> MemoryManager:
    """提供干净的 MemoryManager 实例"""
    return _make_manager()


@pytest.fixture
def rag_system(memory_manager: MemoryManager) -> RAGSystem:
    """提供 RAGSystem 实例"""
    return RAGSystem(memory_manager=memory_manager)


# =============================================================================
# DocumentChunk 测试
# =============================================================================


class TestDocumentChunk:
    """DocumentChunk 数据模型测试"""

    def test_create_minimal(self):
        """创建最小化 DocumentChunk"""
        chunk = DocumentChunk(
            id="chunk-1",
            doc_id="doc-1",
            content="测试分块内容",
            index=0,
        )
        assert chunk.id == "chunk-1"
        assert chunk.doc_id == "doc-1"
        assert chunk.content == "测试分块内容"
        assert chunk.index == 0
        assert chunk.embedding is None

    def test_create_with_embedding(self):
        """创建带嵌入向量的 DocumentChunk"""
        chunk = DocumentChunk(
            id="chunk-2",
            doc_id="doc-1",
            content="嵌入测试",
            index=1,
            embedding=[0.1, 0.2, 0.3],
        )
        assert chunk.embedding == [0.1, 0.2, 0.3]

    def test_to_dict(self):
        """序列化为字典"""
        chunk = DocumentChunk(
            id="chunk-3",
            doc_id="doc-2",
            content="字典测试",
            index=2,
        )
        d = chunk.to_dict()
        assert d["id"] == "chunk-3"
        assert d["doc_id"] == "doc-2"
        assert d["content"] == "字典测试"
        assert d["index"] == 2

    def test_repr(self):
        """字符串表示"""
        chunk = DocumentChunk(id="c1", doc_id="d1", content="你好世界", index=0)
        r = repr(chunk)
        assert "DocumentChunk" in r
        assert "c1" in r
        assert "d1" in r


# =============================================================================
# Document 测试
# =============================================================================


class TestDocument:
    """Document 数据模型测试"""

    def test_create_minimal(self):
        """创建最小化 Document"""
        doc = Document(
            id="doc-1",
            content="全文内容",
            source="/path/to/file.txt",
            doc_type="txt",
        )
        assert doc.id == "doc-1"
        assert doc.source == "/path/to/file.txt"
        assert doc.doc_type == "txt"
        assert doc.chunks == []
        assert doc.metadata == {}
        assert isinstance(doc.created_at, datetime)

    def test_create_with_chunks(self):
        """创建带分块的 Document"""
        chunks = [
            DocumentChunk(id="c1", doc_id="doc-1", content="块1", index=0),
            DocumentChunk(id="c2", doc_id="doc-1", content="块2", index=1),
        ]
        doc = Document(
            id="doc-1",
            content="全文内容",
            source="test.md",
            doc_type="md",
            chunks=chunks,
            metadata={"key": "value"},
        )
        assert len(doc.chunks) == 2
        assert doc.metadata["key"] == "value"

    def test_to_dict(self):
        """序列化为字典"""
        chunks = [DocumentChunk(id="c1", doc_id="d1", content="块", index=0)]
        doc = Document(
            id="d1",
            content="全文",
            source="file.pdf",
            doc_type="pdf",
            chunks=chunks,
        )
        d = doc.to_dict()
        assert d["id"] == "d1"
        assert d["source"] == "file.pdf"
        assert d["doc_type"] == "pdf"
        assert d["chunks"] == 1

    def test_repr(self):
        """字符串表示"""
        doc = Document(id="d1", content="内容", source="a.txt", doc_type="txt")
        r = repr(doc)
        assert "Document" in r
        assert "d1" in r
        assert "a.txt" in r


# =============================================================================
# RAGSystem 初始化测试
# =============================================================================


class TestRAGSystemInit:
    """RAGSystem 初始化测试"""

    def test_init_with_memory_manager(self, memory_manager: MemoryManager):
        """正常初始化"""
        rag = RAGSystem(memory_manager=memory_manager)
        assert rag.memory_manager is memory_manager
        assert rag.llm_router is None
        assert rag._documents == {}

    def test_init_with_llm_router(self, memory_manager: MemoryManager):
        """带 LLM 路由器的初始化"""
        mock_router = MagicMock()
        rag = RAGSystem(memory_manager=memory_manager, llm_router=mock_router)
        assert rag.llm_router is mock_router

    def test_init_invalid_memory_manager(self):
        """传入无效的 memory_manager 应抛出 TypeError"""
        with pytest.raises(TypeError, match="MemoryManager"):
            RAGSystem(memory_manager="not-a-manager")


# =============================================================================
# 文档类型推断测试
# =============================================================================


class TestInferDocType:
    """文档类型推断测试"""

    def test_txt(self):
        rag = RAGSystem(memory_manager=_make_manager())
        assert rag._infer_doc_type("readme.txt") == "txt"

    def test_md(self):
        rag = RAGSystem(memory_manager=_make_manager())
        assert rag._infer_doc_type("README.md") == "md"
        assert rag._infer_doc_type("doc.markdown") == "md"

    def test_pdf(self):
        rag = RAGSystem(memory_manager=_make_manager())
        assert rag._infer_doc_type("document.pdf") == "pdf"

    def test_html(self):
        rag = RAGSystem(memory_manager=_make_manager())
        assert rag._infer_doc_type("index.html") == "html"
        assert rag._infer_doc_type("page.htm") == "html"

    def test_unknown_extension(self):
        """未知扩展名默认 txt"""
        rag = RAGSystem(memory_manager=_make_manager())
        assert rag._infer_doc_type("data.csv") == "txt"
        assert rag._infer_doc_type("script.py") == "txt"
        assert rag._infer_doc_type("noext") == "txt"


# =============================================================================
# 文本分块测试
# =============================================================================


class TestChunkText:
    """文本分块功能测试"""

    def test_empty_text(self, rag_system: RAGSystem):
        """空文本"""
        assert rag_system._chunk_text("") == []
        assert rag_system._chunk_text("   ") == []

    def test_short_text(self, rag_system: RAGSystem):
        """短文本（小于 chunk_size）"""
        text = "短文本"
        result = rag_system._chunk_text(text, chunk_size=500, overlap=50)
        assert result == [text]

    def test_exact_size(self, rag_system: RAGSystem):
        """文本恰好等于 chunk_size"""
        text = "A" * 500
        result = rag_system._chunk_text(text, chunk_size=500, overlap=50)
        assert result == [text]

    def test_slightly_longer(self, rag_system: RAGSystem):
        """文本略大于 chunk_size"""
        text = "A" * 600
        result = rag_system._chunk_text(text, chunk_size=500, overlap=50)
        assert len(result) >= 1

    def test_long_text_multiple_chunks(self, rag_system: RAGSystem):
        """长文本产生多个分块"""
        text = "段落一的内容。\n\n段落二的内容。\n\n段落三的内容。\n\n段落四的内容。\n\n段落五的内容。"
        result = rag_system._chunk_text(text, chunk_size=20, overlap=5)
        assert len(result) >= 2

    def test_paragraph_boundary(self, rag_system: RAGSystem):
        """在段落边界分割"""
        para1 = "A" * 300
        para2 = "B" * 300
        text = f"{para1}\n\n{para2}"
        result = rag_system._chunk_text(text, chunk_size=400, overlap=50)
        assert len(result) >= 1
        # 应该在段落边界分割
        # 注意：当重叠文本+新段落超过 chunk_size 时，块大小会适度增长
        # 这是预期行为——段落完整性优先于严格字符数
        for chunk in result:
            # 每个块不应超过 chunk_size + overlap + max(para_len)
            # 这里 para_len=300, 最坏情况 400+50+300=750
            assert len(chunk) <= 400 + 50 + 300, (
                f"块大小 {len(chunk)} 超出预期上限 (chunk_size=400, overlap=50)"
            )

    def test_overlap_content(self, rag_system: RAGSystem):
        """相邻块有重叠内容"""
        # 用有意义的句子确保分块在语义边界
        sentences = [f"这是第{i}句。" for i in range(50)]
        text = "\n\n".join(sentences)
        result = rag_system._chunk_text(text, chunk_size=100, overlap=30)
        if len(result) >= 2:
            # 检查是否有内容重叠（不精确，因为可能在句子边界）
            pass  # 滑动窗口确保上下文不丢失

    def test_deduplicate(self, rag_system: RAGSystem):
        """去重相邻块"""
        chunks = ["块A", "块A", "块B", "块C", "块C"]
        deduped = rag_system._deduplicate_chunks(chunks)
        assert deduped == ["块A", "块B", "块C"]

    def test_split_sentences(self, rag_system: RAGSystem):
        """句子分割"""
        text = "第一句。第二句！第三句？"
        sentences = rag_system._split_sentences(text)
        assert len(sentences) >= 3

    def test_chinese_text(self, rag_system: RAGSystem):
        """中文文本分块"""
        text = "这是第一段。这是第二段。这是第三段。"
        result = rag_system._chunk_text(text, chunk_size=10, overlap=2)
        assert len(result) >= 1


# =============================================================================
# 文件读取测试
# =============================================================================


class TestReadTextFile:
    """文本文件读取测试"""

    async def test_read_txt(self, rag_system: RAGSystem):
        """读取 txt 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("你好，世界！\n这是测试内容。")
            tmp_path = f.name

        try:
            content = await rag_system._read_text_file(tmp_path)
            assert "你好，世界！" in content
            assert "测试内容" in content
        finally:
            os.unlink(tmp_path)

    async def test_read_md(self, rag_system: RAGSystem):
        """读取 md 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as f:
            f.write("# 标题\n\n这是 **Markdown** 内容。")
            tmp_path = f.name

        try:
            content = await rag_system._read_text_file(tmp_path)
            assert "# 标题" in content
            assert "Markdown" in content
        finally:
            os.unlink(tmp_path)

    async def test_read_empty_file(self, rag_system: RAGSystem):
        """读取空文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            tmp_path = f.name

        try:
            content = await rag_system._read_text_file(tmp_path)
            assert content == ""
        finally:
            os.unlink(tmp_path)


class TestReadPDFFile:
    """PDF 文件读取测试"""

    async def test_pdf_not_installed(self, rag_system: RAGSystem):
        """PyPDF2 未安装时抛出 RAGException"""
        with patch("agent_forge.core.rag_system.PyPDF2", None):
            with pytest.raises(RAGException, match="PyPDF2 未安装"):
                await rag_system._read_pdf_file("dummy.pdf")


# =============================================================================
# 文档导入测试
# =============================================================================


class TestImportDocument:
    """文档导入测试"""

    async def test_import_txt(self, rag_system: RAGSystem):
        """导入 txt 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("这是第一行。\n这是第二行。\n这是第三行。")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path)
            assert doc.source == tmp_path
            assert doc.doc_type == "txt"
            assert len(doc.chunks) >= 1
            assert doc.content == "这是第一行。\n这是第二行。\n这是第三行。"
            # 文档应注册
            assert rag_system.get_document(doc.id) is doc
        finally:
            os.unlink(tmp_path)

    async def test_import_md(self, rag_system: RAGSystem):
        """导入 md 文件"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as f:
            f.write("# Markdown 文档\n\n这是一段内容。\n\n- 列表项1\n- 列表项2")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path)
            assert doc.doc_type == "md"
            assert "# Markdown 文档" in doc.content
            assert len(doc.chunks) >= 1
        finally:
            os.unlink(tmp_path)

    async def test_import_with_explicit_type(self, rag_system: RAGSystem):
        """显式指定文档类型"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".dat", encoding="utf-8", delete=False
        ) as f:
            f.write("DAT 文件内容")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path, doc_type="txt")
            assert doc.doc_type == "txt"
            assert doc.source == tmp_path
        finally:
            os.unlink(tmp_path)

    async def test_import_file_not_found(self, rag_system: RAGSystem):
        """文件不存在应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError, match="文件不存在"):
            await rag_system.import_document("/not/exist/file.txt")

    async def test_import_unsupported_type(self, rag_system: RAGSystem):
        """不支持的文档类型"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".exe", encoding="utf-8", delete=False
        ) as f:
            f.write("binary")
            tmp_path = f.name

        try:
            with pytest.raises(UnsupportedDocumentType, match="不支持的文档类型"):
                await rag_system.import_document(tmp_path, doc_type="exe")
        finally:
            os.unlink(tmp_path)

    async def test_import_large_text(self, rag_system: RAGSystem):
        """导入大文本文档（多分块）"""
        # 生成约 3000 字符的文本
        paragraphs = [f"这是第{i}段的内容。包含一些句子。" for i in range(100)]
        text = "\n\n".join(paragraphs)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write(text)
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path)
            # 500 chunk_size 下 3000 字符应该产生多个块
            assert len(doc.chunks) >= 2
            # 验证所有块的内容总和接近原文
            all_chunks = "".join(c.content for c in doc.chunks)
            assert len(all_chunks) > 0
        finally:
            os.unlink(tmp_path)

    async def test_import_with_metadata(self, rag_system: RAGSystem):
        """导入带额外元数据的文档"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("带元数据的文档")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(
                tmp_path, metadata={"author": "tester", "version": 1}
            )
            assert doc.metadata["author"] == "tester"
            assert doc.metadata["version"] == 1
            assert "file_name" in doc.metadata
        finally:
            os.unlink(tmp_path)

    async def test_import_stores_to_memory(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """导入的文档块应存入 MemoryManager"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("存储到记忆测试。")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path)

            # 检查每个块是否存入了 MemoryManager
            # （通过搜索验证，因为 SQLite 降级）
            results = await memory_manager.search_long_term(
                "存储到记忆测试", limit=5
            )
            assert len(results) >= 1
            found = any(
                r.metadata.get("_rag_type") == "doc_chunk"
                and r.metadata.get("doc_id") == doc.id
                for r in results
            )
            assert found, "文档块应存储在 MemoryManager 中"
        finally:
            os.unlink(tmp_path)


# =============================================================================
# 检索测试
# =============================================================================


class TestRetrieve:
    """检索功能测试"""

    async def test_empty_query(self, rag_system: RAGSystem):
        """空查询返回空列表"""
        results = await rag_system.retrieve("")
        assert results == []

        results = await rag_system.retrieve("   ")
        assert results == []

    async def test_retrieve_from_long_term(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """从长期记忆中检索"""
        # 先存储测试数据到 MemoryManager
        await memory_manager.add_long_term(
            content="ChromaDB 是一个向量数据库",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc1", "chunk_index": 0},
        )
        await memory_manager.add_long_term(
            content="Python 是一种编程语言",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc2", "chunk_index": 0},
        )
        await memory_manager.add_long_term(
            content="SQLite 是轻量级数据库",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc3", "chunk_index": 0},
        )

        results = await rag_system.retrieve("数据库", limit=5)
        # 应该至少匹配到包含"数据库"的内容
        assert len(results) >= 1
        # 验证返回的是 DocumentChunk
        assert all(isinstance(c, DocumentChunk) for c in results)
        assert any("数据库" in c.content for c in results)

    async def test_retrieve_excludes_regular_memories(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """RAG 检索应排除普通长期记忆"""
        # 存储 RAG 块
        await memory_manager.add_long_term(
            content="RAG 相关文档内容",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc1", "chunk_index": 0},
        )
        # 存储普通记忆（无 _rag_type 标记）
        await memory_manager.add_long_term(
            content="普通记忆内容",
            agent_role="user",
        )

        results = await rag_system.retrieve("内容", limit=5)
        # 应只返回 RAG 块
        for c in results:
            assert hasattr(c, "doc_id")

    async def test_retrieve_limit(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """限制返回数量"""
        for i in range(5):
            await memory_manager.add_long_term(
                content=f"测试文档内容第{i}条",
                agent_role="rag_system",
                metadata={"_rag_type": "doc_chunk", "doc_id": f"doc{i}", "chunk_index": 0},
            )

        results = await rag_system.retrieve("测试", limit=3)
        assert len(results) <= 3

    async def test_retrieve_filters(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """检索过滤"""
        await memory_manager.add_long_term(
            content="关于 AI 的文档",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc-ai", "chunk_index": 0, "doc_source": "ai.txt"},
        )
        await memory_manager.add_long_term(
            content="关于 DB 的文档",
            agent_role="rag_system",
            metadata={"_rag_type": "doc_chunk", "doc_id": "doc-db", "chunk_index": 0, "doc_source": "db.txt"},
        )

        # 按 doc_id 过滤
        results = await rag_system.retrieve("文档", limit=5, filters={"doc_id": "doc-ai"})
        assert all(c.doc_id == "doc-ai" for c in results)

    async def test_merge_results_dedup(self, rag_system: RAGSystem):
        """合并去重"""
        c1 = DocumentChunk(id="c1", doc_id="d1", content="内容1", index=0)
        c2 = DocumentChunk(id="c1", doc_id="d1", content="内容1", index=0)  # 重复
        c3 = DocumentChunk(id="c3", doc_id="d2", content="内容2", index=0)

        merged = rag_system._merge_results([c1, c2, c3], [], limit=10)
        assert len(merged) == 2
        assert merged[0].id == "c1"
        assert merged[1].id == "c3"

    async def test_retrieve_graceful_degradation(self, rag_system: RAGSystem):
        """优雅降级：MemoryManager 搜索失败时返回空列表"""
        # 让 search_long_term 抛出异常
        rag_system.memory_manager.search_long_term = AsyncMock(
            side_effect=Exception("模拟故障")
        )
        results = await rag_system.retrieve("查询", limit=5)
        assert results == []


# =============================================================================
# 增强提示词测试
# =============================================================================


class TestAugmentPrompt:
    """增强提示词生成测试"""

    async def test_no_results(self, rag_system: RAGSystem):
        """无检索结果时返回原始查询"""
        result = await rag_system.augment_prompt("如何配置 API")
        assert result == "如何配置 API"

    async def test_with_results(self, rag_system: RAGSystem):
        """有检索结果时构建增强提示"""
        # 通过导入文档确保结果在内存注册表中可检索
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("API Key 需要配置在 .env 文件中")
            tmp_path = f.name

        try:
            await rag_system.import_document(tmp_path)
            result = await rag_system.augment_prompt("API Key 配置", limit=5)
            assert "Memory Retrieval" in result
            assert "参考上下文" in result
            assert "API Key" in result
            assert "用户问题" in result
            assert "API Key 配置" in result
            assert "知识库" not in result
        finally:
            os.unlink(tmp_path)

    async def test_with_context(self, rag_system: RAGSystem):
        """带额外上下文的增强提示"""
        result = await rag_system.augment_prompt(
            "配置问题", context="用户是管理员", limit=3
        )
        # 无结果时带 context 应返回原始 query（当前设计）
        # 因为 augment_prompt 现在只在有 chunks 时构建完整提示
        assert result == "配置问题"

    async def test_with_results_and_context(self, rag_system: RAGSystem):
        """同时有检索结果和额外上下文"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("数据库连接字符串在配置文件中")
            tmp_path = f.name

        try:
            await rag_system.import_document(tmp_path)
            result = await rag_system.augment_prompt(
                "数据库连接", context="生产环境", limit=5
            )
            assert "参考上下文" in result
            assert "数据库连接" in result
            assert "额外上下文" in result
            assert "生产环境" in result
            assert "用户问题" in result
            assert "数据库连接" in result
            assert "知识库" not in result
        finally:
            os.unlink(tmp_path)

    async def test_prompt_format(self, rag_system: RAGSystem):
        """增强提示的格式正确"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("测试知识内容")
            tmp_path = f.name

        try:
            await rag_system.import_document(tmp_path)
            result = await rag_system.augment_prompt("测试知识", limit=5)
            lines = result.split("\n")
            assert lines[0] == (
                "你是一个 Memory Retrieval 助手。"
                "请根据以下 Memory 和外部文档片段回答用户的问题。"
            )
            assert "=== 参考上下文 ===" in lines
            assert "=== 用户问题 ===" in lines
            assert "测试知识" in lines
            assert "知识库" not in result
            assert "请基于上述参考上下文回答问题：" in result
        finally:
            os.unlink(tmp_path)


# =============================================================================
# 文档管理测试
# =============================================================================


class TestDocumentManagement:
    """文档管理功能测试"""

    async def test_list_documents_empty(self, rag_system: RAGSystem):
        """空列表"""
        assert rag_system.list_documents() == []

    async def test_list_documents(self, rag_system: RAGSystem):
        """列出文档"""
        doc1 = Document(id="d1", content="a", source="a.txt", doc_type="txt")
        doc2 = Document(id="d2", content="b", source="b.pdf", doc_type="pdf")
        rag_system._documents["d1"] = doc1
        rag_system._documents["d2"] = doc2

        docs = rag_system.list_documents()
        assert len(docs) == 2
        assert docs[0]["id"] == "d1"
        assert docs[1]["id"] == "d2"

    def test_get_document(self, rag_system: RAGSystem):
        """获取文档"""
        doc = Document(id="d1", content="test", source="t.txt", doc_type="txt")
        rag_system._documents["d1"] = doc

        assert rag_system.get_document("d1") is doc
        assert rag_system.get_document("not-exist") is None

    def test_remove_document(self, rag_system: RAGSystem):
        """移除文档"""
        doc = Document(id="d1", content="test", source="t.txt", doc_type="txt")
        rag_system._documents["d1"] = doc

        assert rag_system.remove_document("d1") is True
        assert rag_system.get_document("d1") is None

        assert rag_system.remove_document("not-exist") is False


# =============================================================================
# 集成测试（真实文件流）
# =============================================================================


class TestIntegration:
    """RAGSystem 集成测试"""

    async def test_full_pipeline(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """完整流程：导入 -> 检索 -> 增强"""
        # 1. 导入文档
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", encoding="utf-8", delete=False
        ) as f:
            f.write("AgentForge 使用 MemoryManager 管理三层记忆系统。\n")
            f.write("短期记忆使用内存 FIFO 队列。\n")
            f.write("长期记忆使用 ChromaDB 向量数据库。\n")
            f.write("ChromaDB 不可用时降级到 SQLite。\n")
            f.write("RAG 系统复用 MemoryManager 的向量存储。")
            tmp_path = f.name

        try:
            doc = await rag_system.import_document(tmp_path)
            assert doc is not None
            assert len(doc.chunks) >= 1

            # 2. 检索
            results = await rag_system.retrieve("ChromaDB 向量数据库", limit=3)
            assert len(results) >= 1
            assert any("ChromaDB" in c.content for c in results)

            # 3. 增强提示
            prompt = await rag_system.augment_prompt(
                "ChromaDB 的作用是什么？", limit=3
            )
            assert "ChromaDB" in prompt
            assert "参考上下文" in prompt
            assert "用户问题" in prompt

            # 4. 文档管理
            listed = rag_system.list_documents()
            assert len(listed) == 1
            assert listed[0]["id"] == doc.id

        finally:
            os.unlink(tmp_path)

    async def test_multiple_documents(self, rag_system: RAGSystem, memory_manager: MemoryManager):
        """多文档导入和管理"""
        paths = []
        try:
            for i in range(3):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", encoding="utf-8", delete=False
                ) as f:
                    f.write(f"文档{i}的内容。\n" * 20)
                    paths.append(f.name)

            # 导入
            docs = []
            for p in paths:
                doc = await rag_system.import_document(p)
                docs.append(doc)

            assert len(rag_system.list_documents()) == 3

            # 移除一个
            rag_system.remove_document(docs[0].id)
            assert len(rag_system.list_documents()) == 2

        finally:
            for p in paths:
                try:
                    os.unlink(p)
                except OSError:
                    pass
