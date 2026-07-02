"""
AgentForge Memory Retrieval 后端

提供文档导入、分块、向量化存储和语义检索功能。
作为 Memory 的执行上下文检索能力，复用 MemoryManager 的向量存储（ChromaDB/SQLite）和嵌入能力。

设计原则：
- 文档块通过 add_long_term 存入 MemoryManager，元数据标记来源
- 检索时合并长期记忆和外部记忆结果
- ChromaDB 不可用时降级到文本匹配
- 读取支持 txt/md/pdf 格式
"""
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None  # type: ignore


@dataclass
class DocumentChunk:
    """文档分块

    表示文档被分割后的一个独立片段，包含文本内容和位置信息。
    """

    id: str
    doc_id: str
    content: str
    index: int  # 在原文中的位置（0-based）
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "content": self.content,
            "index": self.index,
        }

    def __repr__(self) -> str:
        return (
            f"<DocumentChunk(id={self.id!r}, doc_id={self.doc_id!r}, "
            f"index={self.index}, content_preview={self.content[:40]!r}...)>"
        )


@dataclass
class Document:
    """文档

    表示一个被导入的完整文档，包含原始内容和分块结果。
    """

    id: str
    content: str
    source: str  # 文件路径或 URL
    doc_type: str  # pdf, txt, md, html
    chunks: List[DocumentChunk] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content_preview": self.content[:100],
            "source": self.source,
            "doc_type": self.doc_type,
            "chunks": len(self.chunks),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id!r}, source={self.source!r}, "
            f"type={self.doc_type!r}, chunks={len(self.chunks)})>"
        )


class RAGException(Exception):
    """Memory Retrieval 异常基类 — 用于区分检索后端错误与其他异常"""
    pass


class DocumentNotFoundException(RAGException):
    """文档未找到"""
    pass


class UnsupportedDocumentType(RAGException):
    """不支持的文档类型"""
    pass


class RAGSystem:
    """Memory Retrieval 后端

    提供文档导入、分块、向量化和检索功能。
    复用 MemoryManager 的向量存储进行持久化和语义搜索。
    类名保留为 RAGSystem 以兼容现有内部调用。

    使用示例::

        rag = RAGSystem(memory_manager)
        doc = await rag.import_document("readme.md")
        chunks = await rag.retrieve("如何配置 API Key", limit=3)
        prompt = await rag.augment_prompt("如何配置 API Key")
    """

    # 默认分块参数
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50

    # 检索时从不同来源获取的数量倍数
    RETRIEVE_MULTIPLIER = 2

    # 元数据标记，用于区分外部文档片段和普通长期记忆
    RAG_META_KEY = "_rag_type"
    RAG_META_VALUE = "doc_chunk"

    def __init__(
        self,
        memory_manager: Any,
        llm_router: Optional[Any] = None,
    ):
        """初始化 Memory Retrieval 后端

        Args:
            memory_manager: MemoryManager 实例，用于向量存储和检索
            llm_router: 可选的 LLMRouter 实例，用于 query 扩展等增强功能
        """
        from agent_forge.core.memory_manager import MemoryManager

        if not isinstance(memory_manager, MemoryManager):
            raise TypeError("memory_manager 必须是 MemoryManager 实例")

        self.memory_manager = memory_manager
        self.llm_router = llm_router

        # 文档注册表（内存索引）
        # doc_id -> Document
        self._documents: Dict[str, Document] = {}

        logger.info(
            "Memory Retrieval backend initialized, llm_router=%s",
            "available" if llm_router else "not available",
        )

    # =========================================================================
    # 文档导入
    # =========================================================================

    async def import_document(
        self,
        source: str,
        doc_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """导入文档

        流程:
        1. 自动检测文档类型（从文件扩展名）
        2. 读取文件内容
        3. 文本分块（滑动窗口）
        4. 每个分块存入 MemoryManager（长期记忆）
        5. 返回 Document 对象

        Args:
            source: 文件路径
            doc_type: 文档类型（自动从扩展名推断），如 pdf/txt/md
            metadata: 额外的文档元数据

        Returns:
            Document 实例

        Raises:
            FileNotFoundError: 文件不存在
            UnsupportedDocumentType: 不支持的文档类型
            RAGException: 其他读取/处理错误
        """
        # 检查文件是否存在
        if not os.path.isfile(source):
            raise FileNotFoundError(f"文件不存在: {source}")

        # 推断文档类型
        if doc_type is None:
            doc_type = self._infer_doc_type(source)

        # 验证文档类型
        supported_types = {"txt", "md", "pdf"}
        if doc_type not in supported_types:
            raise UnsupportedDocumentType(
                f"不支持的文档类型: {doc_type!r}，支持: {', '.join(sorted(supported_types))}"
            )

        logger.info("开始导入文档: %s (type=%s)", source, doc_type)

        try:
            # 读取文件内容
            content = await self._read_file(source, doc_type)

            # 生成文档 ID
            doc_id = self._generate_doc_id(source, content)

            # 创建 Document 对象
            document = Document(
                id=doc_id,
                content=content,
                source=source,
                doc_type=doc_type,
                metadata={
                    "file_name": os.path.basename(source),
                    "file_size": os.path.getsize(source),
                    **(metadata or {}),
                },
            )

            # 文本分块
            chunk_texts = self._chunk_text(
                content,
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                overlap=self.DEFAULT_CHUNK_OVERLAP,
            )

            # 创建并存储每个分块
            for idx, chunk_content in enumerate(chunk_texts):
                chunk_id = f"{doc_id}:chunk_{idx}"
                chunk = DocumentChunk(
                    id=chunk_id,
                    doc_id=doc_id,
                    content=chunk_content,
                    index=idx,
                )
                document.chunks.append(chunk)

                # 分块存入 MemoryManager（长期记忆）
                await self._store_chunk(chunk, source, doc_type)

            # 注册文档
            self._documents[doc_id] = document

            logger.info(
                "文档导入完成: %s (chunks=%d, total_chars=%d)",
                source,
                len(document.chunks),
                len(content),
            )
            return document

        except FileNotFoundError:
            raise
        except UnsupportedDocumentType:
            raise
        except Exception as exc:
            logger.error("文档导入失败: %s - %s", source, exc)
            raise RAGException(f"文档导入失败: {exc}") from exc

    def _generate_doc_id(self, source: str, content: str) -> str:
        """基于源路径和内容生成稳定的文档 ID"""
        raw = f"{source}:{content[:100]}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    def _infer_doc_type(self, source: str) -> str:
        """从文件扩展名推断文档类型"""
        ext = os.path.splitext(source)[1].lower()
        type_map = {
            ".txt": "txt",
            ".md": "md",
            ".markdown": "md",
            ".pdf": "pdf",
            ".html": "html",
            ".htm": "html",
        }
        inferred = type_map.get(ext, "txt")
        logger.debug("推断文档类型: %s -> %s", ext, inferred)
        return inferred

    # =========================================================================
    # 文件读取
    # =========================================================================

    async def _read_file(self, source: str, doc_type: str) -> str:
        """读取文件内容

        Args:
            source: 文件路径
            doc_type: 文档类型

        Returns:
            文件文本内容

        Raises:
            UnsupportedDocumentType: 不支持的文档类型
        """
        read_methods = {
            "txt": self._read_text_file,
            "md": self._read_text_file,
            "html": self._read_text_file,
            "pdf": self._read_pdf_file,
        }

        method = read_methods.get(doc_type)
        if method is None:
            raise UnsupportedDocumentType(f"不支持的文档类型: {doc_type!r}")

        return await method(source)

    async def _read_text_file(self, source: str) -> str:
        """读取文本文件（txt/md/html）"""
        loop = self._get_event_loop()

        def _read() -> str:
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        try:
            content = await loop.run_in_executor(None, _read)
            if not content.strip():
                logger.warning("文件内容为空: %s", source)
            return content
        except Exception as exc:
            logger.error("读取文本文件失败: %s - %s", source, exc)
            # 尝试以二进制模式读取
            try:
                with open(source, "rb") as f:
                    raw = f.read()
                return raw.decode("utf-8", errors="replace")
            except Exception as bin_err:
                raise RAGException(f"读取文件失败: {bin_err}") from exc

    async def _read_pdf_file(self, source: str) -> str:
        """读取 PDF 文件

        使用 PyPDF2 库提取文本内容。
        """
        if PyPDF2 is None:
            raise RAGException(
                "PyPDF2 未安装，无法读取 PDF 文件。请执行: pip install PyPDF2"
            )

        loop = self._get_event_loop()

        def _read_pdf() -> str:
            pages = []
            try:
                with open(source, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page_num, page in enumerate(reader.pages):
                        try:
                            text = page.extract_text()
                            if text.strip():
                                pages.append(text)
                        except Exception as page_err:
                            logger.warning(
                                "PDF 第 %d 页提取失败: %s", page_num + 1, page_err
                            )
                    return "\n\n".join(pages)
            except Exception as exc:
                raise RAGException(f"读取 PDF 失败: {exc}") from exc

        content = await loop.run_in_executor(None, _read_pdf)
        if not content.strip():
            logger.warning("PDF 内容为空: %s", source)

        return content

    @staticmethod
    def _get_event_loop():
        """获取当前事件循环（兼容不同 Python 版本）"""
        import asyncio

        try:
            return asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.new_event_loop()

    # =========================================================================
    # 文本分块
    # =========================================================================

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> List[str]:
        """文本分块

        将长文本分割成重叠的块，优先在段落边界分割。
        使用滑动窗口确保上下文连续性。

        Args:
            text: 输入文本
            chunk_size: 每个块的目标字符数
            overlap: 相邻块之间的重叠字符数

        Returns:
            分块后的文本列表
        """
        if not text:
            return []

        text = text.strip()
        if not text:
            return []

        if len(text) <= chunk_size:
            return [text]

        # 先按段落分割
        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current_chunk: List[str] = []
        current_length = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)

            # 如果段落本身超过 chunk_size，需要进一步拆分
            if para_len > chunk_size:
                # 先 flush 当前累积
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # 将长段落按句子拆分
                sentences = self._split_sentences(para)
                temp_buf: List[str] = []
                temp_len = 0

                for sent in sentences:
                    sent_len = len(sent)
                    if temp_len + sent_len > chunk_size and temp_buf:
                        chunks.append("".join(temp_buf))
                        # 保留末尾句子作为 overlap
                        overlap_text = self._get_overlap_from_chunk(
                            "".join(temp_buf), overlap
                        )
                        temp_buf = [overlap_text] if overlap_text else []
                        temp_len = len(overlap_text)

                    temp_buf.append(sent)
                    temp_len += sent_len

                if temp_buf:
                    chunks.append("".join(temp_buf))
                continue

            # 如果加上当前段落超过 chunk_size，开始新块
            if current_length + para_len > chunk_size and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append(chunk_text)

                # 计算 overlap：从当前块尾部取 overlap 字符
                overlap_text = self._get_overlap_from_chunk(chunk_text, overlap)
                current_chunk = [overlap_text] if overlap_text else []
                current_length = len(overlap_text)

            current_chunk.append(para)
            current_length += para_len + 2  # +2 for "\n\n"

        # 处理剩余的块
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        # 去重（相邻块如果内容完全一致则合并）
        deduped = self._deduplicate_chunks(chunks)

        logger.debug(
            "文本分块: %d chars -> %d chunks (chunk_size=%d, overlap=%d)",
            len(text),
            len(deduped),
            chunk_size,
            overlap,
        )
        return deduped

    def _split_sentences(self, text: str) -> List[str]:
        """将文本分割为句子

        使用标点符号（。！？.!\n）作为分割点。
        """
        import re

        # 保留分割符
        parts = re.split(r"([。！？.!?\n])", text)
        sentences: List[str] = []
        buf = ""
        for part in parts:
            buf += part
            if part in ("。", "！", "？", ".", "!", "?", "\n") and buf.strip():
                sentences.append(buf.strip() + " ")
                buf = ""
        if buf.strip():
            sentences.append(buf.strip())
        return sentences

    def _get_overlap_from_chunk(self, chunk_text: str, overlap: int) -> str:
        """从块末尾提取 overlap 字符

        尝试在句子边界截断，避免截断单词/句子。
        """
        if len(chunk_text) <= overlap:
            return chunk_text

        # 从末尾往前找句子边界
        end = chunk_text[overlap:] if overlap < len(chunk_text) else chunk_text
        return end

    def _deduplicate_chunks(self, chunks: List[str]) -> List[str]:
        """去重相邻的重复块"""
        if not chunks:
            return []

        result = [chunks[0]]
        for chunk in chunks[1:]:
            if chunk != result[-1]:
                result.append(chunk)
        return result

    # =========================================================================
    # 分块存储
    # =========================================================================

    async def _store_chunk(
        self,
        chunk: DocumentChunk,
        source: str,
        doc_type: str,
    ) -> None:
        """将单个分块存入 MemoryManager

        使用 add_long_term 存储，元数据标记为外部文档片段。
        ChromaDB 不可用时自动降级到 SQLite。

        Args:
            chunk: 文档分块
            source: 源文件路径
            doc_type: 文档类型
        """
        try:
            # 构造元数据，用于检索时过滤和展示
            meta = {
                self.RAG_META_KEY: self.RAG_META_VALUE,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.index,
                "doc_source": source,
                "doc_type": doc_type,
                "chunk_id": chunk.id,
            }

            await self.memory_manager.add_long_term(
                content=chunk.content,
                agent_role="rag_system",
                metadata=meta,
            )

        except Exception as exc:
            logger.error(
                "存储分块失败 (doc=%s, chunk=%d): %s",
                chunk.doc_id,
                chunk.index,
                exc,
            )
            # 不抛出——单个分块存储失败不应中断整个导入

    # =========================================================================
    # 检索
    # =========================================================================

    async def retrieve(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """检索相关文档块

        流程:
        1. 从 MemoryManager 长期记忆搜索（优先向量检索，降级文本匹配）
        2. 从 MemoryManager 外部记忆搜索
        3. 合并结果，过滤出外部文档片段
        4. 按相关性排序，去重

        Args:
            query: 搜索查询
            limit: 最大返回结果数
            filters: 过滤条件（保留参数，当前未实现）

        Returns:
            匹配的 DocumentChunk 列表
        """
        if not query or not query.strip():
            logger.warning("检索查询为空")
            return []

        logger.info("Memory Retrieval: query=%s, limit=%d", query[:50], limit)

        # 步骤 1: 从长期记忆搜索
        long_term_results = await self._search_long_term(query, limit)

        # 步骤 2: 从外部记忆搜索
        external_results = await self._search_external(query, limit)

        # 步骤 3: 合并与去重
        merged = self._merge_results(long_term_results, external_results, limit)

        # 步骤 4: 如果 MemoryManager 搜索结果不足，从内存文档注册表补充
        # （SQLite 降级时关键词 AND 匹配可能遗漏结果）
        if len(merged) < limit:
            fallback_results = self._search_in_memory(query, limit - len(merged))
            for chunk in fallback_results:
                if chunk.id not in {c.id for c in merged}:
                    merged.append(chunk)

        if filters:
            merged = self._apply_filters(merged, filters)

        logger.info(
            "Memory Retrieval complete: query=%s, found=%d "
            "(long_term=%d, external=%d, memory=%d)",
            query[:30],
            len(merged),
            len(long_term_results),
            len(external_results),
            max(0, len(merged) - len(long_term_results) - len(external_results)),
        )
        return merged[:limit]

    async def _search_long_term(
        self,
        query: str,
        limit: int,
    ) -> List[DocumentChunk]:
        """从长期记忆搜索外部文档片段"""
        try:
            entries = await self.memory_manager.search_long_term(
                query=query,
                limit=limit * self.RETRIEVE_MULTIPLIER,
            )

            chunks = []
            for entry in entries:
                meta = entry.metadata or {}

                # 只取标记为外部文档片段的条目
                if meta.get(self.RAG_META_KEY) == self.RAG_META_VALUE:
                    chunk = DocumentChunk(
                        id=meta.get("chunk_id", entry.id),
                        doc_id=meta.get("doc_id", "unknown"),
                        content=entry.content,
                        index=int(meta.get("chunk_index", 0)),
                        embedding=entry.embedding,
                    )
                    chunks.append(chunk)

            return chunks

        except Exception as exc:
            logger.warning("长期记忆搜索失败，降级处理: %s", exc)
            return []

    async def _search_external(
        self,
        query: str,
        limit: int,
    ) -> List[DocumentChunk]:
        """从外部记忆搜索"""
        try:
            entries = await self.memory_manager.search_external(
                query=query,
                limit=limit * self.RETRIEVE_MULTIPLIER,
            )

            chunks = []
            for entry in entries:
                meta = entry.metadata or {}
                chunk = DocumentChunk(
                    id=meta.get("chunk_id", entry.id),
                    doc_id=meta.get("doc_id", "unknown"),
                    content=entry.content,
                    index=int(meta.get("chunk_index", 0)),
                    embedding=entry.embedding,
                )
                chunks.append(chunk)

            return chunks

        except Exception as exc:
            logger.warning("外部记忆搜索失败: %s", exc)
            return []

    def _merge_results(
        self,
        long_term_chunks: List[DocumentChunk],
        external_chunks: List[DocumentChunk],
        limit: int,
    ) -> List[DocumentChunk]:
        """合并并去重两个来源的结果

        Args:
            long_term_chunks: 长期记忆搜索到的分块
            external_chunks: 外部记忆搜索到的分块
            limit: 返回上限

        Returns:
            合并后的分块列表（按相关性排序）
        """
        seen_ids: set = set()
        merged: List[DocumentChunk] = []

        for chunk in long_term_chunks + external_chunks:
            if chunk.id not in seen_ids:
                seen_ids.add(chunk.id)
                merged.append(chunk)

        return merged[:limit]

    def _search_in_memory(
        self,
        query: str,
        limit: int,
    ) -> List[DocumentChunk]:
        """从内存文档注册表搜索（兜底方案）

        当 MemoryManager 的向量/文本搜索无结果时，
        直接从已导入文档的内存索引中做关键词匹配。

        Args:
            query: 搜索查询
            limit: 最大返回结果数

        Returns:
            匹配的 DocumentChunk 列表
        """
        if not self._documents:
            return []

        query_lower = query.strip().lower()
        keywords = [kw for kw in query_lower.split() if len(kw) >= 2]

        if not keywords:
            return []

        scored: List[tuple[int, DocumentChunk]] = []

        for doc in self._documents.values():
            for chunk in doc.chunks:
                content_lower = chunk.content.lower()
                score = 0

                # 精确匹配子串得分最高
                if query_lower in content_lower:
                    score += 10

                # 关键词匹配
                for kw in keywords:
                    if kw in content_lower:
                        score += 2

                if score > 0:
                    scored.append((score, chunk))

        # 按得分降序
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]

    def _apply_filters(
        self,
        chunks: List[DocumentChunk],
        filters: Dict[str, Any],
    ) -> List[DocumentChunk]:
        """应用过滤条件"""
        if not filters:
            return chunks

        filtered = list(chunks)

        # 按 doc_id 过滤
        if "doc_id" in filters:
            doc_id_filter = filters["doc_id"]
            filtered = [
                c for c in filtered if c.doc_id == doc_id_filter
            ]

        # 按 source 过滤（匹配源路径关键字）
        if "source" in filters:
            source_filter = filters["source"].lower()
            filtered = [
                c
                for c in filtered
                if source_filter in self._get_chunk_source(c).lower()
            ]

        return filtered

    def _get_chunk_source(self, chunk: DocumentChunk) -> str:
        """从文档注册表获取分块的源路径"""
        doc = self._documents.get(chunk.doc_id)
        return doc.source if doc else ""

    # =========================================================================
    # 增强提示词
    # =========================================================================

    async def augment_prompt(
        self,
        query: str,
        context: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """生成增强提示

        检索相关 Memory 和外部文档片段，组装成增强的提示词。
        格式: "根据以下参考上下文回答用户问题:\n\n[上下文片段1]\n...\n\n用户问题: ..."

        Args:
            query: 用户查询
            context: 额外上下文（可选）
            limit: 检索的文档块数量

        Returns:
            增强后的提示词字符串
        """
        logger.info("生成增强提示: query=%s", query[:50])

        # 检索相关文档块
        chunks = await self.retrieve(query, limit=limit)

        if not chunks:
            logger.info("未找到相关文档，使用原始查询")
            return query

        # 构建增强提示
        parts: List[str] = [
            "你是一个 Memory Retrieval 助手。请根据以下 Memory 和外部文档片段回答用户的问题。",
            "如果参考上下文不足以回答问题，请如实说明，不要编造信息。",
            "",
            "=== 参考上下文 ===",
        ]

        for i, chunk in enumerate(chunks, 1):
            source_info = ""
            doc = self._documents.get(chunk.doc_id)
            if doc:
                source_info = f"（来源: {doc.source} ）"
            parts.append(f"[上下文片段 {i}]{source_info}")
            parts.append(chunk.content)
            parts.append("")

        if context:
            parts.append("=== 额外上下文 ===")
            parts.append(context)
            parts.append("")

        parts.append("=== 用户问题 ===")
        parts.append(query)
        parts.append("")
        parts.append("请基于上述参考上下文回答问题：")

        result = "\n".join(parts)

        logger.info(
            "增强提示生成完成: query=%s, chunks=%d, total_chars=%d",
            query[:30],
            len(chunks),
            len(result),
        )
        return result

    # =========================================================================
    # 文档管理
    # =========================================================================

    def list_documents(self) -> List[Dict[str, Any]]:
        """列出所有已导入文档

        Returns:
            文档摘要信息列表
        """
        return [doc.to_dict() for doc in self._documents.values()]

    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档详情

        Args:
            doc_id: 文档 ID

        Returns:
            Document 实例，不存在时返回 None
        """
        return self._documents.get(doc_id)

    def remove_document(self, doc_id: str) -> bool:
        """从注册表移除文档（不删除 MemoryManager 中的存储）

        注意：此方法仅从 RAGSystem 的内存注册表中移除。
        已存入 MemoryManager 的数据不会被删除。

        Args:
            doc_id: 文档 ID

        Returns:
            是否成功移除
        """
        if doc_id in self._documents:
            del self._documents[doc_id]
            logger.info("文档已移除: %s", doc_id)
            return True
        logger.warning("文档不存在: %s", doc_id)
        return False


__all__ = [
    "Document",
    "DocumentChunk",
    "RAGSystem",
    "RAGException",
    "DocumentNotFoundException",
    "UnsupportedDocumentType",
]
