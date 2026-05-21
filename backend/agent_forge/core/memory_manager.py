"""
AgentForge 三层记忆管理系统

提供短期记忆（内存）、长期记忆（ChromaDB/SQLite）、外部记忆（Mock）统一接口。

设计原则：
- 短期记忆：内存 List，FIFO 淘汰，最大 50 条
- 长期记忆：优先 ChromaDB 向量存储，降级到 SQLite 文本匹配
- 外部记忆：Mock 实现，可后续接入真实知识库
"""
import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from asyncio import Lock

from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    """记忆类型枚举"""

    SHORT_TERM = "short_term"  # 短期记忆（内存）
    LONG_TERM = "long_term"  # 长期记忆（ChromaDB / SQLite）
    EXTERNAL = "external"  # 外部记忆（知识库/文档）


class MemoryEntry:
    """记忆条目

    表示一条独立的记忆记录，包含内容、元数据和向量嵌入。
    """

    def __init__(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
        entry_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = entry_id or str(uuid.uuid4())
        self.content = content
        self.memory_type = memory_type
        self.agent_id = agent_id
        self.agent_role = agent_role
        self.task_id = task_id
        self.source = source
        self.created_at = created_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}
        self.embedding = embedding

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "task_id": self.task_id,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return (
            f"<MemoryEntry(id={self.id!r}, type={self.memory_type.value!r}, "
            f"content_preview={self.content[:40]!r}...)>"
        )


class MemoryManager:
    """三层记忆管理器

    管理 Agent 的短期/长期/外部记忆，支持向 LLM 提示词注入上下文。

    使用示例::

        mm = MemoryManager()
        await mm.add_short_term("用户偏好: 喜欢简洁风格")
        entries = await mm.get_short_term(agent_id="agent-1")
        context = await mm.get_context(agent_id="agent-1")

        await mm.add_long_term("重要知识: Python 3.11 新特性")
        results = await mm.search_long_term("Python 新特性")
    """

    # 默认配置
    DEFAULT_MAX_SHORT_TERM = 50
    DEFAULT_LONG_TERM_LIMIT = 5

    def __init__(
        self,
        llm_router: Optional[Any] = None,
        chroma_client: Optional[Any] = None,
        max_short_term: int = DEFAULT_MAX_SHORT_TERM,
    ):
        self.llm_router = llm_router
        self.chroma_client = chroma_client

        # 短期记忆（内存）
        self.short_term: List[MemoryEntry] = []
        self.max_short_term = max_short_term

        # ChromaDB 集合（惰性初始化）
        self._chroma_collection = None
        self._chroma_available: Optional[bool] = None

        # 异步锁
        self._lock = Lock()

        logger.info(
            "MemoryManager initialized, max_short_term=%d", self.max_short_term
        )

    # =========================================================================
    # 内部工具方法
    # =========================================================================

    def _compute_id(self, content: str, prefix: str = "mem") -> str:
        """基于内容哈希生成稳定 ID"""
        raw = f"{prefix}:{content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _get_embedding_sync(self, text: str) -> Optional[List[float]]:
        """同步方式获取文本嵌入向量

        如果 llm_router 支持 embedding，调用之。
        否则返回 None（降级为全文匹配）。
        """
        if self.llm_router is None:
            return None
        try:
            # 尝试调用 llm_router 的 embedding 方法
            if hasattr(self.llm_router, "embed") and callable(self.llm_router.embed):
                # 部分 LLM 客户端 embedding 是同步的
                result = self.llm_router.embed(text)
                if result is not None and isinstance(result, list):
                    return result
            if hasattr(self.llm_router, "embed_async"):
                # 异步 embedding —— 调用方应使用 _get_embedding_async
                return None
        except Exception as exc:
            logger.warning("Failed to get embedding: %s", exc)
        return None

    async def _get_embedding(self, text: str) -> Optional[List[float]]:
        """获取文本嵌入向量（异步优先）"""
        if self.llm_router is None:
            return None
        try:
            if hasattr(self.llm_router, "embed_async") and callable(
                self.llm_router.embed_async
            ):
                result = await self.llm_router.embed_async(text)
                if result is not None and isinstance(result, list):
                    return result
        except Exception as exc:
            logger.warning("Async embedding failed: %s", exc)
        # 降级到同步
        return self._get_embedding_sync(text)

    # =========================================================================
    # ChromaDB 初始化
    # =========================================================================

    def _init_chroma(self) -> bool:
        """初始化 ChromaDB 客户端和集合

        Returns:
            True 表示 ChromaDB 可用，False 表示降级
        """
        if self._chroma_available is not None:
            return self._chroma_available

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            if self.chroma_client is None:
                from agent_forge.config.settings import settings

                persist_dir = settings.CHROMA_PERSIST_DIR
                self.chroma_client = chromadb.PersistentClient(
                    path=persist_dir,
                    settings=ChromaSettings(anonymized_telemetry=False),
                )

            # 获取或创建集合
            self._chroma_collection = self.chroma_client.get_or_create_collection(
                name="agentforge_memories",
                metadata={"description": "AgentForge 长期记忆存储"},
            )
            self._chroma_available = True
            logger.info("ChromaDB initialized successfully")
            return True

        except Exception as exc:
            logger.warning(
                "ChromaDB unavailable, falling back to SQLite: %s", exc
            )
            self._chroma_available = False
            return False

    # =========================================================================
    # 短期记忆操作（内存）
    # =========================================================================

    async def add_short_term(
        self,
        content: str,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """添加短期记忆

        Args:
            content: 记忆内容
            agent_id: 关联的 Agent ID
            agent_role: 关联的 Agent 角色
            task_id: 关联的任务 ID
            metadata: 额外元数据

        Returns:
            创建的 MemoryEntry
        """
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.SHORT_TERM,
            agent_id=agent_id,
            agent_role=agent_role,
            task_id=task_id,
            metadata=metadata,
        )

        async with self._lock:
            self.short_term.append(entry)
            # FIFO 淘汰
            if len(self.short_term) > self.max_short_term:
                removed = self.short_term.pop(0)
                logger.debug("Short-term FIFO evicted: %s", removed.id)

        logger.debug("Added short-term memory: %s", entry.id)
        return entry

    async def get_short_term(
        self,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """获取短期记忆

        Args:
            agent_id: 按 Agent ID 过滤（None 不过滤）
            limit: 最大返回条数

        Returns:
            匹配的记忆条目列表
        """
        async with self._lock:
            if agent_id is None:
                entries = list(self.short_term)
            else:
                entries = [e for e in self.short_term if e.agent_id == agent_id]

        # 返回最新的 N 条
        return entries[-limit:]

    async def clear_short_term(
        self, agent_id: Optional[str] = None
    ) -> int:
        """清空短期记忆

        Args:
            agent_id: 仅清空指定 Agent 的记忆（None 清空全部）

        Returns:
            清空的条目数
        """
        async with self._lock:
            if agent_id is None:
                count = len(self.short_term)
                self.short_term.clear()
            else:
                before = len(self.short_term)
                self.short_term = [
                    e for e in self.short_term if e.agent_id != agent_id
                ]
                count = before - len(self.short_term)

        logger.info("Cleared %d short-term memories (agent_id=%s)", count, agent_id)
        return count

    # =========================================================================
    # 长期记忆操作（ChromaDB / SQLite）
    # =========================================================================

    async def add_long_term(
        self,
        content: str,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """添加长期记忆

        优先存入 ChromaDB，降级到 SQLite。

        Args:
            content: 记忆内容
            agent_id: 关联的 Agent ID
            agent_role: 关联的 Agent 角色
            task_id: 关联的任务 ID
            metadata: 额外元数据

        Returns:
            创建的 MemoryEntry
        """
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.LONG_TERM,
            agent_id=agent_id,
            agent_role=agent_role,
            task_id=task_id,
            metadata=metadata,
        )

        # 尝试生成嵌入向量
        embedding = await self._get_embedding(content)
        entry.embedding = embedding

        # 优先 ChromaDB
        if self._init_chroma():
            try:
                self._chroma_collection.add(
                    ids=[entry.id],
                    documents=[content],
                    metadatas=[{
                        "agent_id": agent_id or "",
                        "agent_role": agent_role or "",
                        "task_id": task_id or "",
                        "created_at": entry.created_at.isoformat(),
                        **(metadata or {}),
                    }],
                    embeddings=[embedding] if embedding else None,
                )
                logger.debug("Added long-term memory to ChromaDB: %s", entry.id)
                return entry
            except Exception as exc:
                logger.warning(
                    "ChromaDB add failed, falling back to SQLite: %s", exc
                )

        # 降级到 SQLite
        await self._add_long_term_sqlite(entry)
        return entry

    async def _add_long_term_sqlite(self, entry: MemoryEntry) -> None:
        """将长期记忆写入 SQLite（降级路径）"""
        try:
            from agent_forge.database.connection import async_session
            from agent_forge.database.models import MemoryORM

            async with async_session() as session:
                orm_entry = MemoryORM(
                    id=entry.id,
                    content=entry.content,
                    memory_type="long_term",
                    agent_id=entry.agent_id,
                    agent_role=entry.agent_role,
                    task_id=entry.task_id,
                    created_at=entry.created_at,
                    metadata_json=entry.metadata,
                )
                session.add(orm_entry)
                await session.commit()

            logger.debug("Added long-term memory to SQLite: %s", entry.id)

        except Exception as exc:
            logger.error("SQLite fallback add failed: %s", exc)

    async def search_long_term(
        self,
        query: str,
        limit: int = 5,
        agent_role: Optional[str] = None,
    ) -> List[MemoryEntry]:
        """语义搜索长期记忆

        优先 ChromaDB 向量搜索，降级到 SQLite 文本匹配。

        Args:
            query: 搜索查询
            limit: 最大返回条数
            agent_role: 按角色过滤

        Returns:
            匹配的记忆条目列表
        """
        # 优先 ChromaDB
        if self._init_chroma():
            try:
                return await self._search_long_term_chroma(query, limit, agent_role)
            except Exception as exc:
                logger.warning(
                    "ChromaDB search failed, falling back to SQLite: %s", exc
                )

        # 降级到 SQLite
        return await self._search_long_term_sqlite(query, limit, agent_role)

    async def _search_long_term_chroma(
        self, query: str, limit: int = 5, agent_role: Optional[str] = None
    ) -> List[MemoryEntry]:
        """ChromaDB 向量搜索"""
        # 尝试生成查询嵌入
        query_embedding = await self._get_embedding(query)

        # 构建过滤条件
        where = None
        if agent_role:
            where = {"agent_role": agent_role}

        if query_embedding:
            results = self._chroma_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where,
            )
        else:
            # 无嵌入时按文本搜索
            results = self._chroma_collection.query(
                query_texts=[query],
                n_results=limit,
                where=where,
            )

        if not results or not results["ids"]:
            return []

        entries = []
        for idx, doc_id in enumerate(results["ids"][0]):
            meta = (results["metadatas"][0][idx]
                    if results.get("metadatas") else {})
            entries.append(MemoryEntry(
                content=results["documents"][0][idx],
                memory_type=MemoryType.LONG_TERM,
                agent_id=meta.get("agent_id") or None,
                agent_role=meta.get("agent_role") or None,
                task_id=meta.get("task_id") or None,
                metadata=meta,
                entry_id=doc_id,
            ))

        return entries

    async def _search_long_term_sqlite(
        self, query: str, limit: int = 5, agent_role: Optional[str] = None
    ) -> List[MemoryEntry]:
        """SQLite 文本匹配搜索（降级路径）"""
        try:
            from sqlalchemy import select

            from agent_forge.database.connection import async_session
            from agent_forge.database.models import MemoryORM

            async with async_session() as session:
                stmt = select(MemoryORM).where(
                    MemoryORM.memory_type == "long_term"
                )

                if agent_role:
                    stmt = stmt.where(MemoryORM.agent_role == agent_role)

                # 简单关键词匹配（SQLite LIKE）
                # 将查询分词后逐个匹配
                keywords = query.strip().split()
                for kw in keywords:
                    if len(kw) >= 2:  # 忽略单字符词
                        stmt = stmt.where(
                            MemoryORM.content.ilike(f"%{kw}%")
                        )

                stmt = stmt.order_by(MemoryORM.created_at.desc()).limit(limit)
                result = await session.execute(stmt)
                rows = result.scalars().all()

                return [
                    MemoryEntry(
                        content=row.content,
                        memory_type=MemoryType.LONG_TERM,
                        agent_id=row.agent_id,
                        agent_role=row.agent_role,
                        task_id=row.task_id,
                        metadata=row.metadata_json,
                        entry_id=row.id,
                        created_at=row.created_at,
                    )
                    for row in rows
                ]

        except Exception as exc:
            logger.error("SQLite search failed: %s", exc)
            return []

    async def get_long_term_by_task(
        self, task_id: str
    ) -> List[MemoryEntry]:
        """获取某个任务的所有长期记忆"""
        # 优先 ChromaDB
        if self._init_chroma():
            try:
                results = self._chroma_collection.get(
                    where={"task_id": task_id}
                )
                if results and results["ids"]:
                    entries = []
                    for idx, doc_id in enumerate(results["ids"]):
                        meta = (results["metadatas"][idx]
                                if results.get("metadatas") else {})
                        entries.append(MemoryEntry(
                            content=results["documents"][idx],
                            memory_type=MemoryType.LONG_TERM,
                            agent_id=meta.get("agent_id") or None,
                            agent_role=meta.get("agent_role") or None,
                            task_id=task_id,
                            metadata=meta,
                            entry_id=doc_id,
                        ))
                    return entries
            except Exception as exc:
                logger.warning(
                    "ChromaDB get_by_task failed, fallback to SQLite: %s", exc
                )

        # SQLite 降级
        return await self._get_long_term_by_task_sqlite(task_id)

    async def _get_long_term_by_task_sqlite(
        self, task_id: str
    ) -> List[MemoryEntry]:
        """SQLite 按任务查询"""
        try:
            from sqlalchemy import select

            from agent_forge.database.connection import async_session
            from agent_forge.database.models import MemoryORM

            async with async_session() as session:
                stmt = (
                    select(MemoryORM)
                    .where(MemoryORM.task_id == task_id)
                    .where(MemoryORM.memory_type == "long_term")
                    .order_by(MemoryORM.created_at.desc())
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

                return [
                    MemoryEntry(
                        content=row.content,
                        memory_type=MemoryType.LONG_TERM,
                        agent_id=row.agent_id,
                        agent_role=row.agent_role,
                        task_id=row.task_id,
                        metadata=row.metadata_json,
                        entry_id=row.id,
                        created_at=row.created_at,
                    )
                    for row in rows
                ]

        except Exception as exc:
            logger.error("SQLite get_by_task failed: %s", exc)
            return []

    # =========================================================================
    # 外部记忆操作（Mock）
    # =========================================================================

    async def add_external(
        self,
        content: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """添加外部记忆

        当前为 Mock 实现，仅返回 MemoryEntry 不做持久化。

        Args:
            content: 记忆内容
            source: 来源（如 "knowledge_base", "document"）
            metadata: 额外元数据

        Returns:
            创建的 MemoryEntry
        """
        entry = MemoryEntry(
            content=content,
            memory_type=MemoryType.EXTERNAL,
            source=source,
            metadata=metadata,
        )

        logger.debug("Added external memory (mock): %s from %s", entry.id, source)
        return entry

    async def search_external(
        self,
        query: str,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """搜索外部记忆

        当前为 Mock 实现，返回空列表。

        Args:
            query: 搜索查询
            limit: 最大返回条数

        Returns:
            匹配的记忆条目列表
        """
        logger.debug("External search (mock) for: %s", query)
        # Mock: 返回空列表，后续接入真实知识库
        return []

    # =========================================================================
    # 通用搜索
    # =========================================================================

    async def search(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 5,
    ) -> List[MemoryEntry]:
        """搜索所有记忆（或指定类型）

        Args:
            query: 搜索查询
            memory_type: 记忆类型过滤（None 搜索全部）
            limit: 每类最大返回条数

        Returns:
            合并的去重记忆列表
        """
        results: List[MemoryEntry] = []
        seen_ids: set = set()

        async def _collect(entries: List[MemoryEntry]) -> None:
            for e in entries:
                if e.id not in seen_ids:
                    seen_ids.add(e.id)
                    results.append(e)

        # 搜索短期记忆（文本匹配）
        if memory_type is None or memory_type == MemoryType.SHORT_TERM:
            kw = query.lower()
            async with self._lock:
                matched = [
                    e for e in self.short_term
                    if kw in e.content.lower()
                ]
            await _collect(matched[-limit:])

        # 搜索长期记忆
        if memory_type is None or memory_type == MemoryType.LONG_TERM:
            lt_entries = await self.search_long_term(query, limit=limit)
            await _collect(lt_entries)

        # 搜索外部记忆
        if memory_type is None or memory_type == MemoryType.EXTERNAL:
            ext_entries = await self.search_external(query, limit=limit)
            await _collect(ext_entries)

        return results[:limit]

    # =========================================================================
    # 上下文构建
    # =========================================================================

    async def get_context(
        self,
        agent_id: Optional[str] = None,
        agent_role: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """获取 Agent 的上下文记忆（合并短期 + 长期）

        用于向 LLM 提示词注入记忆上下文。

        Args:
            agent_id: Agent ID
            agent_role: Agent 角色
            task_id: 当前任务 ID
            limit: 最大记忆条数

        Returns:
            格式化的记忆文本
        """
        parts: List[str] = []

        # 1. 短期记忆
        st_entries = await self.get_short_term(agent_id=agent_id, limit=limit)
        if st_entries:
            parts.append("## 短期记忆")
            for i, e in enumerate(st_entries, 1):
                role_tag = f"[{e.agent_role}] " if e.agent_role else ""
                parts.append(f"{i}. {role_tag}{e.content}")

        # 2. 长期记忆（按角色和任务搜索）
        lt_entries: List[MemoryEntry] = []

        if task_id:
            lt_entries.extend(
                await self.get_long_term_by_task(task_id)
            )

        if agent_role:
            role_entries = await self.search_long_term(
                query="", limit=limit, agent_role=agent_role
            )
            lt_entries.extend(role_entries)

        # 去重
        if lt_entries:
            seen = set()
            unique_lt = []
            for e in lt_entries:
                if e.id not in seen:
                    seen.add(e.id)
                    unique_lt.append(e)

            parts.append("## 长期记忆")
            for i, e in enumerate(unique_lt[:limit], 1):
                parts.append(f"{i}. {e.content}")

        # 3. 组装
        if not parts:
            return "（暂无记忆上下文）"

        return "\n".join(parts)
