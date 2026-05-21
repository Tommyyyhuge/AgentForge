"""
工具注册中心模块测试
"""
from unittest.mock import MagicMock

import pytest

from agent_forge.mcp.tool_registry import ToolRegistry
from agent_forge.tools.base import BaseTool, ToolSchema


class MockTool(BaseTool):
    """测试用的模拟工具"""

    name = "mock_tool"
    description = "模拟工具用于测试"

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={"input": {"type": "string"}},
            required=["input"],
        )

    async def execute(self, **kwargs) -> str:
        return f"Mock result: {kwargs}"


class MockTool2(BaseTool):
    """另一个模拟工具"""

    name = "mock_tool_2"
    description = "第二个模拟工具"

    def _build_schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters={})

    async def execute(self, **kwargs) -> str:
        return "Result 2"


class TestToolRegistry:
    """测试工具注册中心"""

    @pytest.fixture
    def registry(self):
        return ToolRegistry()

    @pytest.fixture
    def tool1(self):
        return MockTool()

    @pytest.fixture
    def tool2(self):
        return MockTool2()

    def test_register_tool(self, registry, tool1):
        """测试注册工具"""
        registry.register(tool1)
        assert "mock_tool" in registry
        assert registry.count == 1

    def test_register_with_category(self, registry, tool1):
        """测试按类别注册"""
        registry.register(tool1, category="test")
        tools = registry.list_tools(category="test")
        assert len(tools) == 1
        assert tools[0]["name"] == "mock_tool"

    def test_register_duplicate(self, registry, tool1):
        """测试重复注册"""
        registry.register(tool1)
        with pytest.raises(ValueError) as exc_info:
            registry.register(tool1)
        assert "已存在" in str(exc_info.value)

    def test_get_tool(self, registry, tool1):
        """测试获取工具"""
        registry.register(tool1)
        tool = registry.get("mock_tool")
        assert tool is not None
        assert tool.name == "mock_tool"

    def test_get_tool_not_found(self, registry):
        """测试获取不存在的工具"""
        tool = registry.get("nonexistent")
        assert tool is None

    def test_get_required_tool(self, registry, tool1):
        """测试获取必须存在的工具"""
        registry.register(tool1)
        tool = registry.get_required("mock_tool")
        assert tool.name == "mock_tool"

    def test_get_required_not_found(self, registry):
        """测试获取必须存在的工具但不存在"""
        with pytest.raises(KeyError) as exc_info:
            registry.get_required("nonexistent")
        assert "未注册" in str(exc_info.value)

    def test_list_tools(self, registry, tool1, tool2):
        """测试列出所有工具"""
        registry.register(tool1, category="cat1")
        registry.register(tool2, category="cat2")

        tools = registry.list_tools()
        assert len(tools) == 2
        names = [t["name"] for t in tools]
        assert "mock_tool" in names
        assert "mock_tool_2" in names

    def test_list_tools_by_category(self, registry, tool1, tool2):
        """测试按类别列出工具"""
        registry.register(tool1, category="cat1")
        registry.register(tool2, category="cat2")

        tools = registry.list_tools(category="cat1")
        assert len(tools) == 1
        assert tools[0]["name"] == "mock_tool"

    def test_list_categories(self, registry, tool1, tool2):
        """测试列出类别"""
        registry.register(tool1, category="cat1")
        registry.register(tool2, category="cat2")

        categories = registry.list_categories()
        assert "cat1" in categories
        assert "cat2" in categories

    def test_unregister(self, registry, tool1):
        """测试注销工具"""
        registry.register(tool1)
        result = registry.unregister("mock_tool")
        assert result is True
        assert "mock_tool" not in registry

    def test_unregister_not_found(self, registry):
        """测试注销不存在的工具"""
        result = registry.unregister("nonexistent")
        assert result is False

    def test_clear(self, registry, tool1, tool2):
        """测试清空所有工具"""
        registry.register(tool1)
        registry.register(tool2)
        registry.clear()
        assert len(registry) == 0
        assert registry.count == 0

    def test_contains(self, registry, tool1):
        """测试包含检查"""
        registry.register(tool1)
        assert "mock_tool" in registry
        assert "nonexistent" not in registry

    def test_len(self, registry, tool1, tool2):
        """测试长度"""
        registry.register(tool1)
        registry.register(tool2)
        assert len(registry) == 2

    def test_get_tools_for_llm(self, registry, tool1):
        """测试获取 LLM 格式的工具列表"""
        registry.register(tool1)
        tools = registry.get_tools_for_llm()
        assert len(tools) == 1
        assert tools[0]["name"] == "mock_tool"
        assert "parameters" in tools[0]

    def test_register_many(self, registry, tool1, tool2):
        """测试批量注册"""
        registry.register_many([tool1, tool2])
        assert len(registry) == 2

    def test_register_many_duplicate(self, registry, tool1):
        """测试批量注册跳过重复"""
        registry.register(tool1)
        # 再次批量注册，包含已存在的工具
        registry.register_many([tool1])
        # 应该只有一个工具，不会报错
        assert len(registry) == 1

    def test_list_tools_with_schema(self, registry, tool1):
        """测试列出工具包含 schema"""
        registry.register(tool1)
        tools = registry.list_tools(include_schema=True)
        assert "schema" in tools[0]

    def test_list_tools_without_schema(self, registry, tool1):
        """测试列出工具不包含 schema"""
        registry.register(tool1)
        tools = registry.list_tools(include_schema=False)
        assert "schema" not in tools[0]
