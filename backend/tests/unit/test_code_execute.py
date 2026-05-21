"""
安全代码执行工具测试

测试 CodeExecuteTool 的安全扫描、超时控制、输出截断等功能。
"""
import pytest

from agent_forge.tools.code_execute import CodeExecuteTool


class TestCodeExecuteTool:
    """测试安全代码执行工具"""

    @pytest.fixture
    def tool(self):
        return CodeExecuteTool()

    @pytest.mark.asyncio
    async def test_safe_code_execution(self, tool):
        """测试安全代码正常执行：1+1=2"""
        result = await tool.execute(code="print(1+1)")
        assert "2" in result
        assert "[代码执行" not in result

    @pytest.mark.asyncio
    async def test_forbidden_module_import(self, tool):
        """测试禁止导入 os/sys/socket 等模块"""
        # import os
        result = await tool.execute(code="import os\nprint('ok')")
        assert "禁止导入模块" in result or "禁止" in result

        # import sys
        result = await tool.execute(code="import sys\nprint('ok')")
        assert "禁止导入模块" in result or "禁止" in result

        # from os import path
        result = await tool.execute(code="from os import path\nprint('ok')")
        assert "禁止导入模块" in result or "禁止" in result

    @pytest.mark.asyncio
    async def test_forbidden_function(self, tool):
        """测试禁止调用 eval/exec/compile"""
        # eval
        result = await tool.execute(code="eval('1+1')")
        assert "禁止调用" in result

        # exec
        result = await tool.execute(code="exec('print(1)')")
        assert "禁止调用" in result

        # compile
        result = await tool.execute(code="compile('print(1)', '', 'exec')")
        assert "禁止调用" in result

    @pytest.mark.asyncio
    async def test_timeout_handling(self, tool):
        """测试超时处理：长时间运行的代码被终止"""
        result = await tool.execute(
            code="import time; time.sleep(100); print('done')",
            timeout=1,
        )
        assert "超时" in result or "终止" in result

    @pytest.mark.asyncio
    async def test_syntax_error(self, tool):
        """测试语法错误处理"""
        result = await tool.execute(code="print(1+")
        assert "语法错误" in result

    @pytest.mark.asyncio
    async def test_output_truncation(self, tool):
        """测试输出截断：超长输出被截断"""
        # 生成超过 10000 字符的输出
        result = await tool.execute(code="print('x' * 15000)")
        assert "截断" in result or len(result) <= 10050

    @pytest.mark.asyncio
    async def test_empty_code(self, tool):
        """测试空代码处理"""
        result = await tool.execute(code="")
        assert "不能为空" in result

    @pytest.mark.asyncio
    async def test_code_with_stderr(self, tool):
        """测试标准错误输出——使用除零错误触发 stderr"""
        result = await tool.execute(code="print(1/0)")
        assert "标准错误输出" in result or "ZeroDivisionError" in result or "division by zero" in result
