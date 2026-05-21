"""
AgentForge 记忆搜索工具（真实版本）

接入 RAGSystem，支持搜索历史记忆和知识库文档。
提供 Agent 在 ReAct 循环中查询相关上下文的能力。

功能：
- 语义搜索：通过 RAGSystem 检索文档块和记忆
- 关键词降级：向量检索不可用时自动降级到文本匹配
- 格式化输出：结构化的搜索结果展示
"""
import logging
from typing import Any, Dict, List, Optional

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)


class MemorySearchTool(BaseTool):
    """记忆搜索工具

    接入 RAGSystem 的检索增强能力，支持：
    - 知识库文档搜索（已导入的文档）
    - 长期记忆搜索
    - 外部记忆搜索

    当 RAGSystem 不可用时，返回提示信息而非模拟数据。
    """

    name: str = "memory_search"
    description: str = "搜索知识库文档和历史记忆，获取与查询相关的上下文信息"
    version: str = "2.0"

    def __init__(self, rag_system: Optional[Any] = None):
        """初始化记忆搜索工具

        Args:
            rag_system: RAGSystem 实例，可选。为 None 时返回降级提示。
        """
        # 先调用父类 __init__（构建 schema）
        super().__init__()
        self.rag_system = rag_system

        if rag_system is not None:
            logger.info("MemorySearchTool 已接入 RAGSystem")
        else:
            logger.warning("MemorySearchTool 未配置 RAGSystem，将返回降级提示")

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义记忆搜索工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "query": {
                    "type": "string",
                    "description": "搜索查询，描述需要查找的知识或记忆内容",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回的最大结果数量，默认 5",
                    "default": 5,
                },
            },
            required=["query"],
            examples=[
                {"query": "关于 API 配置的说明", "limit": 3},
                {"query": "项目架构设计", "limit": 5},
                {"query": "数据库连接配置", "limit": 5},
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行知识库和记忆搜索

        通过 RAGSystem 检索相关文档块和记忆条目。
        结果按相关性排序，以结构化文本返回。

        Args:
            **kwargs: 工具参数，包含:
                - query: 搜索查询字符串
                - limit: 最大返回结果数（默认 5）

        Returns:
            格式化后的搜索结果字符串
        """
        query: str = kwargs.get("query", "")
        limit: int = kwargs.get("limit", 5)

        logger.info("memory_search 查询: %s (limit=%d)", query, limit)

        if not query or not query.strip():
            return "[记忆搜索错误] 查询不能为空，请提供有效的搜索关键词"

        # 参数约束
        limit = max(1, min(limit, 20))

        # 使用 RAGSystem 检索
        if self.rag_system is not None:
            return await self._search_with_rag(query, limit)
        else:
            return self._fallback_message()

    async def _search_with_rag(self, query: str, limit: int) -> str:
        """使用 RAGSystem 执行搜索

        Args:
            query: 搜索查询
            limit: 结果数量上限

        Returns:
            格式化搜索结果
        """
        try:
            chunks = await self.rag_system.retrieve(
                query=query,
                limit=limit,
            )

            if not chunks:
                # 尝试通过增强提示获取上下文
                logger.info("RAG 检索无结果，尝试增强提示: %s", query)
                return (
                    f"[记忆搜索结果]\n"
                    f"查询: {query}\n\n"
                    f"未找到相关记忆或文档。\n\n"
                    f"提示:\n"
                    f"• 确保已通过 import_document 导入相关文档\n"
                    f"• 尝试使用不同的关键词\n"
                    f"• 检查文档是否已正确分块和存储"
                )

            # 格式化结果
            lines: List[str] = [
                f"[记忆搜索结果]",
                f"查询: {query}",
                f"找到 {len(chunks)} 条相关结果:",
                "",
            ]

            for i, chunk in enumerate(chunks, 1):
                # 获取文档来源信息
                doc_info = await self._get_doc_info(chunk.doc_id)

                lines.extend([
                    f"--- 结果 {i} ---",
                    f"内容: {chunk.content.strip()}",
                ])

                if doc_info:
                    lines.append(f"来源: {doc_info}")

                lines.append(f"文档块: {chunk.id}")
                lines.append("")

            result = "\n".join(lines).strip()
            logger.info("memory_search 返回 %d 条结果", len(chunks))
            return result

        except Exception as exc:
            logger.error("RAGSystem 检索失败: %s", exc)
            return (
                f"[记忆搜索错误]\n"
                f"检索过程中发生错误: {exc}\n\n"
                f"请检查 RAG 系统配置是否正确。"
            )

    async def _get_doc_info(self, doc_id: str) -> str:
        """获取文档来源信息

        Args:
            doc_id: 文档 ID

        Returns:
            文档来源描述，如果不可用返回空字符串
        """
        if self.rag_system is None:
            return ""

        try:
            doc = self.rag_system.get_document(doc_id)
            if doc:
                return f"{doc.source} (类型: {doc.doc_type})"
        except Exception:
            pass

        return ""

    def _fallback_message(self) -> str:
        """RAGSystem 未配置时的降级提示"""
        return (
            "[记忆搜索结果]\n"
            "RAG系统未初始化，无法搜索知识库。\n\n"
            "请确保 MemoryManager 和 RAGSystem 已正确配置。\n"
            "使用方法:\n"
            "  1. 初始化 MemoryManager\n"
            "  2. 创建 RAGSystem(memory_manager)\n"
            "  3. 使用 rag.import_document() 导入文档\n"
            "  4. 将 RAGSystem 注入 MemorySearchTool"
        )


__all__ = ["MemorySearchTool"]
