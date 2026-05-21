"""
AgentForge 文本摘要工具模块

提供基于 LLM 的文本摘要功能。
短文本自动跳过，长文本调用 LLM 进行智能摘要。
"""
import logging
from typing import Any, Dict, List, Optional

from agent_forge.core.llm_client import LLMRouter
from agent_forge.tools.base import BaseTool, ToolSchema
from agent_forge.utils.logging import get_logger

logger: logging.Logger = get_logger(__name__)

# 短文本阈值：低于此长度的文本直接返回，不调用 LLM
_SHORT_TEXT_THRESHOLD: int = 500

# 默认的摘要系统提示词
_SUMMARIZE_SYSTEM_PROMPT: str = (
    "你是一个专业的文本摘要助手。请对以下文本进行简洁、准确的摘要，"
    "保留核心信息和关键数据。使用中文输出。"
)


class SummarizeTool(BaseTool):
    """文本摘要工具

    对文本内容进行智能摘要。
    - 短文本（<500 字）直接返回原始内容
    - 长文本调用 LLM 生成指定长度的摘要
    """

    name: str = "summarize"
    description: str = "对文本进行智能摘要，支持指定摘要长度"
    version: str = "1.0"

    def __init__(self, llm_router: Optional[LLMRouter] = None):
        """初始化摘要工具

        Args:
            llm_router: LLM 路由器实例，未提供时自动创建
        """
        self._llm_router: LLMRouter = llm_router or LLMRouter()
        super().__init__()

    def _build_schema(self) -> ToolSchema:
        """构建工具模式定义

        Returns:
            ToolSchema 实例，定义摘要工具的参数规范
        """
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters={
                "text": {
                    "type": "string",
                    "description": "需要摘要的原始文本内容",
                },
                "max_length": {
                    "type": "integer",
                    "description": "摘要最大字数，默认 200",
                    "default": 200,
                },
            },
            required=["text"],
            examples=[
                {
                    "text": "很长的一段文本...",
                    "max_length": 100,
                },
                {
                    "text": "短文本",
                },
            ],
        )

    async def execute(self, **kwargs) -> str:
        """执行文本摘要

        Args:
            **kwargs: 工具参数，包含:
                - text: 需要摘要的原始文本
                - max_length: 摘要最大字数（默认 200）

        Returns:
            摘要结果字符串
        """
        text: str = kwargs.get("text", "")
        max_length: int = kwargs.get("max_length", 200)

        logger.info(
            "summarize 开始处理文本 (长度=%d, max_length=%d)",
            len(text) if text else 0,
            max_length,
        )

        if not text or not text.strip():
            return "[摘要错误] 文本内容不能为空"

        text = text.strip()
        text_len: int = len(text)

        # 短文本直接返回
        if text_len < _SHORT_TEXT_THRESHOLD:
            logger.info(
                "summarize 文本较短 (%d < %d)，直接返回",
                text_len,
                _SHORT_TEXT_THRESHOLD,
            )
            return text

        # 参数校验
        if max_length < 10:
            return "[摘要错误] 摘要长度不能小于 10"
        if max_length > 10000:
            return "[摘要错误] 摘要长度不能超过 10000"

        # 调用 LLM 进行摘要
        try:
            user_prompt: str = (
                f"请对以下文本进行摘要，摘要字数控制在 {max_length} 字以内。\n\n"
                f"---文本开始---\n{text}\n---文本结束---"
            )

            llm_response = await self._llm_router.route(
                messages=[
                    {"role": "system", "content": _SUMMARIZE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                complexity="simple",
                temperature=0.3,
            )

            summary: str = llm_response.content.strip()
            logger.info(
                "summarize 摘要完成 (原始=%d 字, 摘要=%d 字)",
                text_len,
                len(summary),
            )
            return summary

        except Exception as e:
            logger.error("summarize LLM 调用失败: %s", e)
            return (
                f"[摘要错误] LLM 摘要生成失败: {e}\n"
                f"原始文本 ({text_len} 字) 的前 500 字:\n{text[:500]}"
            )


__all__ = ["SummarizeTool"]
