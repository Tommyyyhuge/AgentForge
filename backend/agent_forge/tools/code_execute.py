"""
AgentForge 安全代码执行工具模块

支持在隔离的子进程中执行 Python 代码片段。
包含 AST 静态扫描、禁止模块/函数拦截、超时控制和输出截断。
"""
import ast
import asyncio
import logging
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 禁止导入的模块（存在安全风险）
FORBIDDEN_MODULES: Set[str] = {
    "os", "sys", "subprocess", "shutil", "socket", "requests",
}

# 禁止调用的内置函数
FORBIDDEN_FUNCTIONS: Set[str] = {
    "eval", "exec", "compile", "__import__", "open",
}

# 默认执行超时（秒）
_DEFAULT_TIMEOUT: int = 30

# 输出最大字符数
_MAX_OUTPUT_LENGTH: int = 10000


class CodeSecurityError(Exception):
    """代码安全异常 - 检测到不安全的代码结构"""

    pass


class CodeExecuteTool(BaseTool):
    """安全代码执行工具

    在隔离的子进程中执行 Python 代码片段。
    执行前进行 AST 静态分析，拦截不安全的模块和函数调用。
    支持超时控制和输出截断。
    """

    name: str = "code_execute"
    description: str = "在隔离环境中运行 Python 代码，支持超时和输出截断"
    version: str = "1.0"

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义代码执行工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码字符串",
                },
                "timeout": {
                    "type": "integer",
                    "description": "执行超时秒数，默认 30，最大 120",
                    "default": _DEFAULT_TIMEOUT,
                },
            },
            required=["code"],
            examples=[
                {"code": "print('Hello, AgentForge!')", "timeout": 10},
                {"code": "result = sum(range(100)); print(result)"},
            ],
        )

    def _ast_scan(self, code: str) -> None:
        """AST 静态扫描，检查代码安全性

        扫描代码的 AST 树，检测：
        - 禁止导入的模块（os, sys, subprocess 等）
        - 禁止调用的函数（eval, exec, compile 等）
        - 不安全的属性访问（如 os.system, subprocess.call）

        Args:
            code: 要检查的 Python 代码

        Raises:
            CodeSecurityError: 检测到不安全代码时抛出
            SyntaxError: 代码语法错误时抛出
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise CodeSecurityError(f"代码语法错误: {e}")

        for node in ast.walk(tree):
            # 检查 import xxx
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        raise CodeSecurityError(
                            f"禁止导入模块: {alias.name}。"
                            f"安全原因不允许使用此模块。"
                        )

            # 检查 from xxx import yyy
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module in FORBIDDEN_MODULES:
                    raise CodeSecurityError(
                        f"禁止导入模块: {node.module}"
                    )
                for alias in node.names:
                    if alias.name in FORBIDDEN_FUNCTIONS:
                        raise CodeSecurityError(
                            f"禁止导入函数: {alias.name}"
                        )

            # 检查函数调用
            if isinstance(node, ast.Call):
                # 直接调用禁止函数：eval(x), exec(x)
                if isinstance(node.func, ast.Name):
                    if node.func.id in FORBIDDEN_FUNCTIONS:
                        raise CodeSecurityError(
                            f"禁止调用函数: {node.func.id}()"
                        )

                # 属性调用：os.system(), subprocess.run()
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id in FORBIDDEN_MODULES:
                            raise CodeSecurityError(
                                f"禁止调用模块方法: "
                                f"{node.func.value.id}.{node.func.attr}()"
                            )
                        # 也检查禁止函数作为属性
                        if node.func.attr in FORBIDDEN_FUNCTIONS:
                            raise CodeSecurityError(
                                f"禁止调用: {node.func.value.id}.{node.func.attr}()"
                            )

        logger.debug("AST 扫描通过，代码安全")

    async def execute(self, **kwargs) -> str:
        """执行 Python 代码

        Args:
            **kwargs: 工具参数，包含:
                - code: 要执行的 Python 代码
                - timeout: 超时秒数（默认 30，最大 120）

        Returns:
            代码执行输出字符串
        """
        code: str = kwargs.get("code", "")
        timeout: int = kwargs.get("timeout", _DEFAULT_TIMEOUT)

        logger.info("code_execute 开始执行代码 (长度=%d)", len(code) if code else 0)

        if not code or not code.strip():
            return "[代码执行错误] 代码不能为空"

        # 参数校验
        timeout = max(1, min(timeout, 120))

        # AST 静态扫描
        try:
            self._ast_scan(code)
        except CodeSecurityError as e:
            logger.warning("code_execute 安全拦截: %s", e)
            return f"[代码执行安全错误] {e}"
        except SyntaxError as e:
            return f"[代码执行错误] 语法错误: {e}"

        # 创建临时文件
        file_id: str = uuid.uuid4().hex[:8]
        tmp_dir: Path = Path(tempfile.gettempdir()) / "agentforge_code"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_file: Path = tmp_dir / f"code_{file_id}.py"

        try:
            tmp_file.write_text(code, encoding="utf-8")

            # 子进程隔离执行
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(tmp_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(tmp_dir),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                logger.warning("code_execute 执行超时 (%ds)", timeout)
                return (
                    f"[代码执行超时] 代码执行超过 {timeout} 秒，已被终止\n"
                    f"代码长度: {len(code)} 字符"
                )

            # 解码输出
            stdout_str: str = stdout.decode("utf-8", errors="replace")
            stderr_str: str = stderr.decode("utf-8", errors="replace")

            # 构建结果
            result_parts: List[str] = []
            exit_code: int = process.returncode or 0

            if stdout_str:
                # 输出截断
                if len(stdout_str) > _MAX_OUTPUT_LENGTH:
                    result_parts.append(
                        stdout_str[:_MAX_OUTPUT_LENGTH]
                    )
                    result_parts.append(
                        f"\n... (输出已截断，共 {len(stdout_str)} 字符)"
                    )
                else:
                    result_parts.append(stdout_str)

            if stderr_str:
                truncated_stderr: str = (
                    stderr_str[:_MAX_OUTPUT_LENGTH]
                    if len(stderr_str) > _MAX_OUTPUT_LENGTH
                    else stderr_str
                )
                result_parts.append(
                    f"\n[标准错误输出]\n{truncated_stderr}"
                )

            result: str = "".join(result_parts) if result_parts else "(无输出)"

            logger.info(
                "code_execute 执行完成 (退出码=%d, 输出=%d 字符)",
                exit_code,
                len(stdout_str) + len(stderr_str),
            )
            return result

        except OSError as e:
            logger.error("code_execute 系统错误: %s", e)
            return f"[代码执行错误] 系统错误: {e}"
        finally:
            # 清理临时文件
            try:
                if tmp_file.exists():
                    tmp_file.unlink()
            except OSError:
                pass


__all__ = ["CodeExecuteTool", "CodeSecurityError", "FORBIDDEN_MODULES", "FORBIDDEN_FUNCTIONS"]
