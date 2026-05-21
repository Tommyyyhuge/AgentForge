"""
错误处理模块测试
"""
import pytest

from agent_forge.core.error_handler import (AppException, ErrorCode,
                                            LLMException, NotFoundException,
                                            ValidationException)


class TestAppException:
    """测试应用异常"""

    def test_basic_exception(self):
        """测试基础异常"""
        exc = AppException(
            code=ErrorCode.INTERNAL_ERROR, message="测试错误", status_code=500
        )
        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.message == "测试错误"
        assert exc.status_code == 500

    def test_exception_to_dict(self):
        """测试异常转字典"""
        exc = AppException(
            code=ErrorCode.TASK_NOT_FOUND,
            message="任务不存在",
            details={"task_id": "123"},
            status_code=404,
        )
        data = exc.to_dict()
        assert data["code"] == "40000"
        assert data["message"] == "任务不存在"
        assert data["details"]["task_id"] == "123"

    def test_validation_exception(self):
        """测试验证异常"""
        exc = ValidationException("参数错误", {"field": "name"})
        assert exc.status_code == 400
        assert exc.code == ErrorCode.INVALID_PARAMETER

    def test_not_found_exception(self):
        """测试未找到异常"""
        exc = NotFoundException("任务", "123")
        assert exc.status_code == 404
        assert "123" in exc.message

    def test_llm_exception(self):
        """测试 LLM 异常"""
        exc = LLMException("API 调用失败")
        assert exc.status_code == 502
        assert exc.code == ErrorCode.LLM_CALL_FAILED
