"""
AgentForge 错误处理模块
"""
from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """错误码枚举"""

    UNKNOWN_ERROR = "10000"
    INTERNAL_ERROR = "10001"
    INVALID_PARAMETER = "20000"
    UNAUTHORIZED = "30000"
    FORBIDDEN = "30001"
    TASK_NOT_FOUND = "40000"
    AGENT_NOT_FOUND = "40001"
    LLM_CALL_FAILED = "40002"
    TOOL_EXECUTION_FAILED = "40003"
    RATE_LIMIT_EXCEEDED = "50000"
    SERVICE_UNAVAILABLE = "50001"
    TIMEOUT_ERROR = "50002"


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "status_code": self.status_code,
        }


class ValidationException(AppException):
    """参数验证异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.INVALID_PARAMETER,
            message=message,
            details=details,
            status_code=400,
        )


class AuthenticationException(AppException):
    """认证异常"""

    def __init__(self, message: str = "认证失败"):
        super().__init__(code=ErrorCode.UNAUTHORIZED, message=message, status_code=401)


class NotFoundException(AppException):
    """资源不存在异常"""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=ErrorCode.TASK_NOT_FOUND,
            message=f"{resource} 不存在: {resource_id}",
            status_code=404,
        )


class LLMException(AppException):
    """LLM 调用异常"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.LLM_CALL_FAILED,
            message=message,
            details=details,
            status_code=502,
        )


class ToolExecutionException(AppException):
    """工具执行异常"""

    def __init__(self, tool_name: str, message: str):
        super().__init__(
            code=ErrorCode.TOOL_EXECUTION_FAILED,
            message=f"工具 '{tool_name}' 执行失败: {message}",
            status_code=500,
        )


class RateLimitException(AppException):
    """限流异常"""

    def __init__(self, message: str = "请求过于频繁"):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED, message=message, status_code=429
        )
