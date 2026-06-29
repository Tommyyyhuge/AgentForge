"""
AgentForge 文件读写工具模块

提供安全的文件读取和写入功能，包含路径遍历防护和大小限制。
"""
import logging
from pathlib import Path
from typing import List

from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 安全限制常量
ALLOWED_DIR: Path = Path("./workspace").resolve()
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB


class FileSecurityError(Exception):
    """文件操作安全异常 - 检测到不安全的路径或操作"""

    pass


def _sanitize_path(path: str) -> Path:
    """防止路径遍历攻击

    将相对路径解析为绝对路径后，验证其是否在 ALLOWED_DIR 范围内。

    Args:
        path: 用户提供的文件路径

    Returns:
        安全的绝对路径 Path 对象

    Raises:
        FileSecurityError: 路径存在遍历攻击风险或越权访问
    """
    try:
        # 解析为绝对路径，消除 ../ 等相对路径成分
        resolved: Path = ALLOWED_DIR.joinpath(path).resolve()
    except (ValueError, OSError) as e:
        raise FileSecurityError(f"路径解析失败: {e}")

    # 检查是否仍在允许的目录范围内
    if ALLOWED_DIR not in resolved.parents and resolved != ALLOWED_DIR:
        raise FileSecurityError(
            f"路径越权: {path} 不在允许的工作目录 {ALLOWED_DIR} 内"
        )

    return resolved


class FileReadTool(BaseTool):
    """文件读取工具

    安全地读取工作区内的文件内容，支持限制读取行数。
    自动拦截路径遍历攻击和超大文件。
    """

    name: str = "file_read"
    description: str = "读取工作区文件内容，支持指定行数限制"
    version: str = "1.0"

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义文件读取工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "path": {
                    "type": "string",
                    "description": "文件路径（相对于工作区目录 ./workspace/）",
                },
                "limit": {
                    "type": "integer",
                    "description": "最大读取行数，默认 1000",
                    "default": 1000,
                },
            },
            required=["path"],
            examples=[
                {"path": "data/config.json", "limit": 50},
                {"path": "logs/app.log", "limit": 200},
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行文件读取

        Args:
            **kwargs: 工具参数，包含:
                - path: 文件路径（相对于 ./workspace/）
                - limit: 最大读取行数（默认 1000）

        Returns:
            文件内容字符串

        Raises:
            FileSecurityError: 路径不安全时抛出
            FileNotFoundError: 文件不存在时抛出
        """
        path: str = kwargs.get("path", "")
        limit: int = kwargs.get("limit", 1000)

        logger.info("file_read 开始读取文件: %s (limit=%d)", path, limit)

        if not path or not path.strip():
            return "[文件读取错误] 路径不能为空"

        try:
            safe_path: Path = _sanitize_path(path)
        except FileSecurityError as e:
            logger.warning("file_read 安全拦截: %s", e)
            return f"[文件读取安全错误] {e}"

        if not safe_path.exists():
            logger.warning("file_read 文件不存在: %s", safe_path)
            return f"[文件读取错误] 文件不存在: {path}"

        if not safe_path.is_file():
            logger.warning("file_read 路径不是文件: %s", safe_path)
            return f"[文件读取错误] 路径不是文件: {path}"

        # 检查文件大小（仅在读取前预检）
        file_size: int = safe_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            logger.warning(
                "file_read 文件过大: %s (%d bytes)", safe_path, file_size
            )
            return (
                f"[文件读取错误] 文件大小 ({file_size / 1024 / 1024:.1f}MB) "
                f"超过限制 ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )

        try:
            content: str = safe_path.read_text(encoding="utf-8")
            lines: List[str] = content.splitlines(keepends=True)

            if limit and len(lines) > limit:
                result: str = "".join(lines[:limit])
                result += (
                    f"\n\n... (文件共 {len(lines)} 行，仅显示前 {limit} 行)"
                )
            else:
                result = content

            logger.info(
                "file_read 读取完成: %s (%d 行)", path, min(len(lines), limit)
            )
            return result

        except UnicodeDecodeError:
            logger.warning("file_read 编码错误: %s", safe_path)
            return f"[文件读取错误] 文件不是有效的 UTF-8 编码: {path}"
        except PermissionError:
            logger.warning("file_read 权限拒绝: %s", safe_path)
            return f"[文件读取错误] 权限不足，无法读取: {path}"
        except OSError as e:
            logger.error("file_read 系统错误: %s", e)
            return f"[文件读取错误] 系统错误: {e}"


class FileWriteTool(BaseTool):
    """文件写入工具

    安全地将内容写入工作区内的文件，自动创建父目录。
    拦截路径遍历攻击和超限文件。
    """

    name: str = "file_write"
    description: str = "将内容写入工作区文件，自动创建父目录"
    version: str = "1.0"

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义文件写入工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "path": {
                    "type": "string",
                    "description": "文件路径（相对于工作区目录 ./workspace/）",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
            },
            required=["path", "content"],
            examples=[
                {"path": "output/result.txt", "content": "Hello, AgentForge!"},
                {"path": "data/config.json", "content": '{"key": "value"}'},
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行文件写入

        Args:
            **kwargs: 工具参数，包含:
                - path: 文件路径（相对于 ./workspace/）
                - content: 要写入的内容

        Returns:
            写入结果消息
        """
        path: str = kwargs.get("path", "")
        content: str = kwargs.get("content", "")

        logger.info("file_write 开始写入文件: %s", path)

        if not path or not path.strip():
            return "[文件写入错误] 路径不能为空"

        if content is None:
            return "[文件写入错误] 内容不能为空"

        try:
            safe_path: Path = _sanitize_path(path)
        except FileSecurityError as e:
            logger.warning("file_write 安全拦截: %s", e)
            return f"[文件写入安全错误] {e}"

        # 检查写入大小
        content_bytes: int = len(content.encode("utf-8"))
        if content_bytes > MAX_FILE_SIZE:
            logger.warning(
                "file_write 内容过大: %d bytes", content_bytes
            )
            return (
                f"[文件写入错误] 内容大小 ({content_bytes / 1024 / 1024:.1f}MB) "
                f"超过限制 ({MAX_FILE_SIZE / 1024 / 1024:.0f}MB)"
            )

        try:
            # 自动创建父目录
            safe_path.parent.mkdir(parents=True, exist_ok=True)

            safe_path.write_text(content, encoding="utf-8")

            logger.info(
                "file_write 写入完成: %s (%d bytes)", path, content_bytes
            )
            return (
                f"文件写入成功: {path}\n"
                f"大小: {content_bytes} 字节\n"
                f"路径: {safe_path}"
            )

        except PermissionError:
            logger.warning("file_write 权限拒绝: %s", safe_path)
            return f"[文件写入错误] 权限不足，无法写入: {path}"
        except OSError as e:
            logger.error("file_write 系统错误: %s", e)
            return f"[文件写入错误] 系统错误: {e}"


__all__ = ["FileReadTool", "FileWriteTool", "FileSecurityError", "MAX_FILE_SIZE"]
