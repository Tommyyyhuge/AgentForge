"""
AgentForge 输出验证模块
"""
import json
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError


class ValidationError(Exception):
    """验证错误异常"""

    pass


class OutputValidator:
    """输出验证器

    使用 Pydantic 模型验证和解析 LLM 输出。
    支持字典和 JSON 字符串两种输入格式。
    """

    def __init__(self, model_class: Type[BaseModel]):
        """
        Args:
            model_class: Pydantic 模型类，用于验证输出结构
        """
        self.model_class = model_class

    def validate(self, data: Dict[str, Any]) -> BaseModel:
        """验证字典数据

        Args:
            data: 待验证的字典数据

        Returns:
            验证后的 Pydantic 模型实例

        Raises:
            ValidationError: 验证失败时抛出
        """
        try:
            return self.model_class(**data)
        except PydanticValidationError as e:
            raise ValidationError(f"Schema 验证失败: {e}")

    def validate_json(self, json_str: str) -> BaseModel:
        """验证 JSON 字符串

        Args:
            json_str: JSON 格式的字符串

        Returns:
            验证后的 Pydantic 模型实例

        Raises:
            ValidationError: JSON 解析失败或验证失败时抛出
        """
        try:
            data = json.loads(json_str)
            return self.validate(data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"JSON 解析失败: {e}")

    def validate_with_default(
        self, data: Optional[Dict[str, Any]], default: BaseModel
    ) -> BaseModel:
        """验证数据，失败时返回默认值

        Args:
            data: 待验证的字典数据
            default: 验证失败时返回的默认模型实例

        Returns:
            验证后的模型实例，或默认值
        """
        if data is None:
            return default
        try:
            return self.validate(data)
        except ValidationError:
            return default
