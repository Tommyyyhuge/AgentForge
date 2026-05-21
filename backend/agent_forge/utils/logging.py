"""
AgentForge 日志系统模块
"""
import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from agent_forge.config.settings import settings


class JSONFormatter(logging.Formatter):
    """JSON 格式日志格式化器"""

    def format(self, record: logging.LogRecord) -> str:
        """将日志记录格式化为 JSON 字符串"""
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加额外字段（如果存在）
        if hasattr(record, "extra"):
            log_data["extra"] = record.extra

        # 添加异常信息（如果存在）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False, default=str)


class PlainFormatter(logging.Formatter):
    """纯文本格式日志格式化器"""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def get_formatter(format_type: Optional[str] = None):
    """获取日志格式化器

    Args:
        format_type: 格式类型，"json" 或 "plain"，默认从配置读取

    Returns:
        logging.Formatter 实例
    """
    fmt_type = format_type or settings.LOG_FORMAT
    if fmt_type == "json":
        return JSONFormatter()
    return PlainFormatter()


def setup_logging(
    level: Optional[str] = None,
    format_type: Optional[str] = None,
    handlers: Optional[list] = None,
) -> logging.Logger:
    """配置日志系统

    Args:
        level: 日志级别，默认从配置读取
        format_type: 格式类型，"json" 或 "plain"
        handlers: 自定义处理器列表

    Returns:
        配置好的根日志记录器
    """
    log_level = level or settings.LOG_LEVEL

    # 配置根记录器
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # 清除现有处理器
    logger.handlers.clear()

    # 创建格式化器
    formatter = get_formatter(format_type)

    if handlers:
        for handler in handlers:
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    else:
        # 默认：输出到 stdout
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """获取命名日志记录器

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
):
    """带上下文的日志记录

    Args:
        logger: 日志记录器
        level: 日志级别
        message: 日志消息
        extra: 额外上下文数据
    """
    log_method = getattr(logger, level.lower())
    if extra:
        log_method(message, extra={"extra": extra})
    else:
        log_method(message)
