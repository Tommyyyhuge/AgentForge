"""
AgentForge MCP (Model Context Protocol) 工具注册中心

管理工具的注册、发现和调用。
"""
from typing import Any, Dict, List, Optional

from agent_forge.tools.base import BaseTool
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """工具注册中心

    管理所有可用工具的注册、分类和检索。
    支持按名称、类别查找工具。
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: BaseTool, category: str = "general") -> None:
        """注册工具

        Args:
            tool: 工具实例
            category: 工具类别

        Raises:
            ValueError: 工具名称已存在时抛出
        """
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已存在")

        self._tools[tool.name] = tool

        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)

        logger.info(f"已注册工具: {tool.name} (类别: {category})")

    def register_many(self, tools: List[BaseTool], category: str = "general") -> None:
        """批量注册工具

        Args:
            tools: 工具实例列表
            category: 工具类别
        """
        for tool in tools:
            try:
                self.register(tool, category)
            except ValueError as e:
                logger.warning(f"注册工具失败: {e}")

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具

        Args:
            tool_name: 工具名称

        Returns:
            工具实例，不存在则返回 None
        """
        return self._tools.get(tool_name)

    def get_required(self, tool_name: str) -> BaseTool:
        """获取工具（必须存在）

        Args:
            tool_name: 工具名称

        Returns:
            工具实例

        Raises:
            KeyError: 工具不存在时抛出
        """
        if tool_name not in self._tools:
            raise KeyError(f"工具 '{tool_name}' 未注册")
        return self._tools[tool_name]

    def list_tools(
        self, category: Optional[str] = None, include_schema: bool = True
    ) -> List[Dict[str, Any]]:
        """列出工具

        Args:
            category: 类别过滤，None 则返回所有
            include_schema: 是否包含模式定义

        Returns:
            工具信息列表
        """
        if category:
            tool_names = self._categories.get(category, [])
        else:
            tool_names = list(self._tools.keys())

        result: List[Dict[str, Any]] = []
        for name in tool_names:
            tool = self._tools[name]
            info: Dict[str, Any] = {
                "name": tool.name,
                "description": tool.description,
                "category": self._get_category(name),
            }
            if include_schema:
                info["schema"] = tool.get_schema()
            result.append(info)

        return result

    def list_categories(self) -> List[str]:
        """列出所有类别

        Returns:
            类别名称列表
        """
        return list(self._categories.keys())

    def unregister(self, tool_name: str) -> bool:
        """注销工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功注销
        """
        if tool_name not in self._tools:
            return False

        del self._tools[tool_name]

        # 从类别中移除
        for category, tools in self._categories.items():
            if tool_name in tools:
                tools.remove(tool_name)
                break

        logger.info(f"已注销工具: {tool_name}")
        return True

    def clear(self):
        """清空所有工具"""
        self._tools.clear()
        self._categories.clear()
        logger.info("已清空所有工具")

    def _get_category(self, tool_name: str) -> Optional[str]:
        """获取工具所属类别"""
        for category, tools in self._categories.items():
            if tool_name in tools:
                return category
        return None

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """获取用于 LLM 的工具描述列表

        返回精简的工具信息，适合传递给 LLM 作为上下文。

        Returns:
            工具描述列表
        """
        tools = []
        for name, tool in self._tools.items():
            schema = tool.get_schema()
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": schema.get("parameters", {}),
                    "required": schema.get("required", []),
                }
            )
        return tools

    @property
    def count(self) -> int:
        """已注册工具数量"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否已注册"""
        return tool_name in self._tools

    def __len__(self) -> int:
        """已注册工具数量"""
        return len(self._tools)
