"""
AgentForge 网页搜索工具模块 (Mock 版本)

提供模拟的互联网搜索功能，用于 ReAct 循环的演示和测试。
"""
import logging
from typing import Any, Dict

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 预设搜索结果，覆盖常见查询
_MOCK_RESPONSES: Dict[str, str] = {
    "python asyncio": (
        "Python asyncio 是 Python 3.4+ 引入的异步 I/O 框架。\n"
        "核心概念:\n"
        "- async/await 语法用于定义协程\n"
        "- asyncio.run() 启动事件循环\n"
        "- asyncio.gather() 并发执行多个协程\n"
        "- asyncio.create_task() 创建后台任务\n"
        "参考: https://docs.python.org/3/library/asyncio.html"
    ),
    "fastapi": (
        "FastAPI 是一个现代、高性能的 Python Web 框架。\n"
        "核心特性:\n"
        "- 基于 Starlette 和 Pydantic\n"
        "- 自动生成 OpenAPI 文档\n"
        "- 异步支持 (async/await)\n"
        "- 依赖注入系统\n"
        "- 类型提示驱动的数据校验\n"
        "官方文档: https://fastapi.tiangolo.com/"
    ),
    "sqlalchemy": (
        "SQLAlchemy 是 Python 最流行的 ORM 框架。\n"
        "核心模块:\n"
        "- Core: 提供 SQL Expression Language\n"
        "- ORM: 对象关系映射层\n"
        "- Engine: 数据库连接管理\n"
        "- Session: 事务和会话管理\n"
        "参考: https://docs.sqlalchemy.org/"
    ),
    "pydantic": (
        "Pydantic 是 Python 数据验证库，使用类型注解。\n"
        "核心功能:\n"
        "- BaseModel: 声明式数据模型\n"
        "- 自动类型转换和校验\n"
        "- Field 验证器\n"
        "- JSON Schema 生成\n"
        "参考: https://docs.pydantic.dev/"
    ),
    "react": (
        "React 是由 Meta 维护的前端 JavaScript 库。\n"
        "核心概念:\n"
        "- 组件化 UI 开发\n"
        "- 虚拟 DOM 与 diffing 算法\n"
        "- Hooks (useState, useEffect 等)\n"
        "- JSX 语法\n"
        "参考: https://react.dev/"
    ),
    "agentforge": (
        "AgentForge 是一个企业级多智能体协作任务执行平台。\n"
        "核心方向:\n"
        "- ReAct: 手写推理+行动循环引擎\n"
        "- Plan-and-Solve: 任务规划+依赖图执行\n"
        "- Reflection: 自我反思与纠错机制\n"
        "- Multi-Agent: 多智能体协作与通信\n"
    ),
}


class WebSearchTool(BaseTool):
    """网页搜索工具 (Mock 版本)

    模拟互联网搜索功能。在 ReAct 循环中，Agent 通过此工具获取
    外部信息来辅助推理决策。

    实际部署时需替换为真实的搜索 API（如 SerpAPI、Bing API 等）。
    """

    name: str = "web_search"
    description: str = "搜索互联网信息，获取与查询相关的最新资料和知识"
    version: str = "1.0"

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义搜索工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "query": {
                    "type": "string",
                    "description": "搜索查询字符串",
                },
            },
            required=["query"],
            examples=[
                {"query": "python asyncio"},
                {"query": "fastapi tutorial"},
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行模拟搜索

        Args:
            **kwargs: 工具参数，包含:
                - query: 搜索查询字符串

        Returns:
            搜索结果字符串。匹配预设查询时返回具体内容，
            未知查询返回通用提示模板。
        """
        query: str = kwargs.get("query", "")

        logger.info("web_search 接收到查询: %s", query)

        if not query or not query.strip():
            logger.warning("web_search 收到空查询")
            return "[搜索错误] 查询不能为空，请提供有效的搜索关键词。"

        query_lower: str = query.strip().lower()

        # 尝试精确匹配
        if query_lower in _MOCK_RESPONSES:
            logger.info("web_search 精确匹配: %s", query)
            return _MOCK_RESPONSES[query_lower]

        # 尝试模糊匹配（查询包含关键词）
        for key, response in _MOCK_RESPONSES.items():
            # 双向包含匹配：key in query 或 query in key
            if key in query_lower or any(
                word in query_lower for word in key.split()
            ):
                logger.info("web_search 模糊匹配: %s -> %s", query, key)
                return response

        # 未知查询返回通用模板
        logger.info("web_search 未知查询，返回通用模板: %s", query)
        return (
            f"[模拟搜索结果]\n"
            f"查询: {query}\n\n"
            f"关于「{query}」的搜索结果:\n"
            f"1. 这是一个模拟的搜索工具，实际环境会返回真实搜索结果。\n"
            f"2. 建议在部署时集成 SerpAPI、Bing API 或 Google Custom Search。\n"
            f"3. 您也可以查询预设主题: python asyncio, fastapi, sqlalchemy, "
            f"pydantic, react, agentforge。\n"
        )

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的模式定义（字典格式）

        Returns:
            包含工具元数据和参数定义的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            **self.schema.model_dump(),
        }
