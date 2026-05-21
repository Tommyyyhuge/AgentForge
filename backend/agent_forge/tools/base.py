"""
AgentForge 工具基类模块

定义所有工具的抽象基类和通用接口。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolSchema(BaseModel):
    """工具模式定义"""

    name: str = Field(description="工具名称")
    description: str = Field(description="工具描述")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="工具参数定义 (JSON Schema 格式)"
    )
    required: List[str] = Field(default_factory=list, description="必需参数列表")
    examples: List[Dict[str, Any]] = Field(default_factory=list, description="使用示例")


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = Field(description="是否成功")
    output: str = Field(description="输出内容")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class BaseTool(ABC):
    """工具基类

    所有具体工具必须继承此类并实现必要的方法。
    """

    # 类属性，子类必须覆盖
    name: str = ""
    description: str = ""
    version: str = "1.0"

    def __init__(self):
        """初始化工具，构建模式定义"""
        self.schema = self._build_schema()

    @abstractmethod
    def _build_schema(self) -> ToolSchema:
        """构建工具模式

        Returns:
            ToolSchema 实例，描述工具的参数和用法
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            工具执行结果的字符串表示

        Raises:
            ToolExecutionException: 执行失败时抛出
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具的模式定义（字典格式）

        Returns:
            包含工具元数据和参数定义的字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            **self.schema.model_dump(),
        }

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数是否满足要求

        Args:
            params: 参数字典

        Returns:
            是否通过验证
        """
        required = self.schema.required
        for param in required:
            if param not in params:
                return False
        return True

    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}')>"



