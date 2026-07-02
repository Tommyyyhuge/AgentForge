"""
文件读写工具测试

测试 FileReadTool 和 FileWriteTool 的安全路径校验、文件大小限制、父目录自动创建等。
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_forge.tools.file_io import ALLOWED_DIR, FileReadTool, FileWriteTool


def test_file_tools_do_not_expose_workspace_product_term():
    """工具公开描述不应把文件目录称为 Workspace。"""
    schema_text = (
        str(FileReadTool().get_schema()) + str(FileWriteTool().get_schema())
    )

    assert "Workspace" not in schema_text
    assert "工作区" not in schema_text


class TestFileReadTool:
    """测试文件读取工具"""

    @pytest.fixture
    def tool(self):
        return FileReadTool()

    @pytest.fixture
    def workspace(self, tmp_path):
        """创建临时工作区，并覆盖 ALLOWED_DIR"""
        ws = tmp_path / "workspace"
        ws.mkdir()
        with patch(
            "agent_forge.tools.file_io.ALLOWED_DIR",
            ws.resolve(),
        ):
            yield ws.resolve()

    @pytest.mark.asyncio
    async def test_read_file(self, tool, workspace):
        """测试正常读取文件"""
        test_file = workspace / "test.txt"
        test_file.write_text("Hello, AgentForge!", encoding="utf-8")

        result = await tool.execute(path="test.txt")
        assert "Hello, AgentForge!" in result
        assert "[文件读取错误]" not in result

    @pytest.mark.asyncio
    async def test_write_file(self, workspace):
        """测试正常写入文件"""
        write_tool = FileWriteTool()
        test_file = workspace / "output.txt"

        # 写入文件需要使用 workspace 内路径
        with patch(
            "agent_forge.tools.file_io.ALLOWED_DIR",
            workspace,
        ):
            result = await write_tool.execute(
                path="output.txt",
                content="Hello, World!",
            )

        assert "写入成功" in result
        assert test_file.read_text(encoding="utf-8") == "Hello, World!"

    @pytest.mark.asyncio
    async def test_path_traversal_prevention(self, tool, workspace):
        """测试路径遍历攻击防护：../../../etc/passwd"""
        result = await tool.execute(path="../../../etc/passwd")
        assert "安全错误" in result or "越权" in result

    @pytest.mark.asyncio
    async def test_outside_allowed_dir(self, tool, workspace):
        """测试访问工作区外的文件被阻止"""
        result = await tool.execute(path="../outside_file.txt")
        assert "安全错误" in result or "越权" in result

    @pytest.mark.asyncio
    async def test_file_size_limit(self, tool, workspace):
        """测试文件大小限制：超过 10MB 的文件被阻止"""
        large_file = workspace / "large.bin"
        # 写入 11MB 的数据
        large_file.write_bytes(b"x" * (11 * 1024 * 1024))

        result = await tool.execute(path="large.bin")
        assert "超过限制" in result or "过大" in result

    @pytest.mark.asyncio
    async def test_write_create_parent_dirs(self, workspace):
        """测试写入时自动创建父目录"""
        write_tool = FileWriteTool()
        nested_path = "subdir/nested/deep/file.txt"

        with patch(
            "agent_forge.tools.file_io.ALLOWED_DIR",
            workspace,
        ):
            result = await write_tool.execute(
                path=nested_path,
                content="Nested content",
            )

        assert "写入成功" in result
        assert (workspace / nested_path).exists()
        assert (workspace / nested_path).read_text(encoding="utf-8") == "Nested content"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, tool, workspace):
        """测试读取不存在的文件"""
        result = await tool.execute(path="nonexistent.txt")
        assert "不存在" in result

    @pytest.mark.asyncio
    async def test_read_empty_path(self, tool):
        """测试空路径处理"""
        result = await tool.execute(path="")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_write_none_content(self, workspace):
        """测试写入空内容处理"""
        write_tool = FileWriteTool()

        with patch(
            "agent_forge.tools.file_io.ALLOWED_DIR",
            workspace,
        ):
            result = await write_tool.execute(path="test.txt", content=None)

        assert "不能为空" in result
