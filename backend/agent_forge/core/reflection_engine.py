"""
AgentForge 反思引擎模块

分析 Agent 执行任务的历史，生成结构化反思报告和经验总结。
支持将经验自动存入长期记忆，为后续任务提供上下文参考。
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agent_forge.core.llm_client import LLMRouter
from agent_forge.core.memory_manager import MemoryManager
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, TaskResult, TaskStatus
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)



@dataclass
class ReflectionReport:
    """反思报告

    包含 Agent 任务执行的结构化反思结果，涵盖总结、优缺点、建议和经验。
    """

    task_id: str
    agent_id: str
    agent_role: AgentRole
    success: bool
    summary: str = ""  # 执行总结
    strengths: List[str] = field(default_factory=list)  # 做得好的地方
    weaknesses: List[str] = field(default_factory=list)  # 需要改进的地方
    suggestions: List[str] = field(default_factory=list)  # 改进建议
    learned: str = ""  # 学到的东西
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（便于序列化）"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "agent_role": self.agent_role.value,
            "success": self.success,
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "suggestions": self.suggestions,
            "learned": self.learned,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReflectionReport":
        """从字典恢复"""
        return cls(
            task_id=data["task_id"],
            agent_id=data.get("agent_id", ""),
            agent_role=AgentRole(data["agent_role"]),
            success=data["success"],
            summary=data.get("summary", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestions=data.get("suggestions", []),
            learned=data.get("learned", ""),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if "timestamp" in data
            else datetime.now(timezone.utc),
        )



class ReflectionEngine:
    """反思引擎

    分析 Agent 执行任务的历史，生成反思报告和经验。
    支持将经验自动写入长期记忆，供后续任务参考。

    用法::

        engine = ReflectionEngine(llm_router, memory_manager)
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=all_steps,
            result=result,
        )
    """

    REFLECTION_SYSTEM_PROMPT = (
        "你是一个专业的任务执行分析师。请严格按格式要求分析 Agent "
        "的任务执行过程，生成结构化的反思报告。"
    )

    def __init__(
        self,
        llm_router: LLMRouter,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """
        Args:
            llm_router: LLM 路由器，用于调用模型生成反思
            memory_manager: 可选的记忆管理器，用于持久化经验
        """
        self.llm_router = llm_router
        self.memory_manager = memory_manager
        logger.info("ReflectionEngine 初始化完成")

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    async def reflect(
        self,
        task_id: str,
        agent_id: str,
        agent_role: AgentRole,
        steps: List[AgentStep],
        result: TaskResult,
    ) -> ReflectionReport:
        """对任务执行进行反思

        流程:
        1. 分析执行步骤（统计各类步骤数量、耗时等）
        2. 调用 LLM 生成结构化反思报告
        3. 提取经验并存入长期记忆（如果配置了 MemoryManager）
        4. 返回结构化的 ReflectionReport

        Args:
            task_id: 任务 ID
            agent_id: Agent ID
            agent_role: Agent 角色
            steps: 执行步骤列表
            result: 任务执行结果

        Returns:
            ReflectionReport 实例
        """
        logger.info(
            "开始反思: task_id=%s, agent_id=%s, role=%s, steps=%d",
            task_id,
            agent_id,
            agent_role.value,
            len(steps),
        )

        # 1. 分析执行步骤
        analysis = self._analyze_steps(steps)

        # 2. 调用 LLM 生成反思报告
        report = await self._generate_report(
            task_id=task_id,
            agent_role=agent_role,
            analysis=analysis,
            result=result,
            steps=steps,
        )
        # 补充元信息
        report.agent_id = agent_id

        # 3. 提取经验存入长期记忆
        if self.memory_manager:
            try:
                experience = self._extract_experience(report)
                await self.memory_manager.add_long_term(
                    content=experience,
                    agent_id=agent_id,
                    agent_role=agent_role.value,
                    task_id=task_id,
                    metadata={
                        "type": "reflection",
                        "success": str(report.success),
                    },
                )
                logger.info(
                    "经验已存入长期记忆: task_id=%s, summary=%s",
                    task_id,
                    report.summary[:60],
                )
            except Exception as e:
                logger.warning("经验存入长期记忆失败: %s", e)

        logger.info(
            "反思完成: task_id=%s, success=%s, summary=%s",
            task_id,
            report.success,
            report.summary[:60],
        )
        return report

    async def get_agent_insights(
        self,
        agent_role: AgentRole,
        limit: int = 10,
    ) -> List[str]:
        """获取某个 Agent 角色的经验总结

        从长期记忆中检索该角色的反思经验，可用于为后续任务提供上下文。

        Args:
            agent_role: Agent 角色
            limit: 最大返回条数

        Returns:
            经验文本列表
        """
        if not self.memory_manager:
            logger.warning("没有配置 MemoryManager，无法获取经验总结")
            return []

        try:
            entries = await self.memory_manager.search_long_term(
                query="反思经验",
                limit=limit,
                agent_role=agent_role.value,
            )
            insights = [entry.content for entry in entries]
            logger.debug(
                "获取到 %d 条经验总结 for role=%s", len(insights), agent_role.value
            )
            return insights
        except Exception as e:
            logger.error("获取经验总结失败: %s", e)
            return []

    # ------------------------------------------------------------------
    # 步骤分析
    # ------------------------------------------------------------------

    def _analyze_steps(self, steps: List[AgentStep]) -> Dict[str, Any]:
        """分析执行步骤

        统计各类步骤的数量、工具调用次数、平均耗时等。

        Args:
            steps: Agent 执行步骤列表

        Returns:
            统计信息字典
        """
        total = len(steps)
        thought_count = 0
        action_count = 0
        observation_count = 0
        error_count = 0
        final_count = 0
        tool_call_count = 0
        total_latency = 0

        for step in steps:
            if step.step_type == StepType.THOUGHT:
                thought_count += 1
            elif step.step_type == StepType.ACTION:
                action_count += 1
            elif step.step_type == StepType.OBSERVATION:
                observation_count += 1
            elif step.step_type == StepType.ERROR:
                error_count += 1
            elif step.step_type == StepType.FINAL:
                final_count += 1

            if step.tool_name:
                tool_call_count += 1
            if step.latency_ms is not None:
                total_latency += step.latency_ms

        avg_latency = total_latency / max(total, 1)

        return {
            "total_steps": total,
            "thought_count": thought_count,
            "action_count": action_count,
            "observation_count": observation_count,
            "error_count": error_count,
            "final_count": final_count,
            "tool_call_count": tool_call_count,
            "avg_latency_ms": round(avg_latency, 1),
            "total_latency_ms": total_latency,
        }

    # ------------------------------------------------------------------
    # LLM 报告生成
    # ------------------------------------------------------------------

    async def _generate_report(
        self,
        task_id: str,
        agent_role: AgentRole,
        analysis: Dict[str, Any],
        result: TaskResult,
        steps: List[AgentStep],
    ) -> ReflectionReport:
        """生成反思报告

        使用 LLM 分析执行过程，生成结构化反思报告。
        如果 LLM 调用失败，返回基于统计信息的默认报告。

        Args:
            task_id: 任务 ID
            agent_role: Agent 角色
            analysis: 步骤分析统计
            result: 任务结果
            steps: 执行步骤列表

        Returns:
            ReflectionReport 实例
        """
        success = result.status == TaskStatus.COMPLETED

        # 构建步骤描述
        steps_description = self._format_steps_for_prompt(steps)

        analysis_text = (
            f"- 总步骤数: {analysis['total_steps']}\n"
            f"- 思考步骤: {analysis['thought_count']}\n"
            f"- 行动步骤: {analysis['action_count']}\n"
            f"- 观察步骤: {analysis['observation_count']}\n"
            f"- 错误步骤: {analysis['error_count']}\n"
            f"- 最终步骤: {analysis['final_count']}\n"
            f"- 工具调用: {analysis['tool_call_count']}\n"
            f"- 平均耗时: {analysis['avg_latency_ms']:.0f}ms\n"
            f"- 总耗时: {analysis['total_latency_ms']}ms"
        )

        full_steps_desc = f"## 步骤统计\n{analysis_text}\n\n## 执行步骤\n{steps_description}"
        output = result.output or "(无输出)"
        error_msg = result.error_message or "(无错误)"

        prompt = self._build_reflection_prompt(
            task_id=task_id,
            agent_role=agent_role,
            success=success,
            steps_description=full_steps_desc,
            output=output,
            error_message=error_msg,
        )

        raw_response = ""
        try:
            response = await self.llm_router.chat([  # type: ignore[attr-defined]
                {"role": "system", "content": self.REFLECTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
            raw_response = response.content
            logger.debug("LLM 反思响应收到，长度=%d", len(raw_response))
        except Exception as e:
            logger.warning("LLM 反思调用失败，使用默认报告: %s", e)

        report = self._parse_reflection_response(
            raw_response, task_id, agent_role, success
        )

        # 如果 LLM 响应为空或解析失败，使用分析数据构建默认报告
        if not report.summary:
            if success:
                report.summary = (
                    f"任务顺利完成。共 {analysis['total_steps']} 步，"
                    f"{analysis['error_count']} 个错误。"
                )
            else:
                report.summary = (
                    f"执行失败。共 {analysis['total_steps']} 步，"
                    f"{analysis['error_count']} 个错误。"
                )
        if not report.strengths and success:
            report.strengths = ["任务顺利完成"]
        if not report.weaknesses and analysis["error_count"] > 0:
            report.weaknesses = [f"执行过程中出现 {analysis['error_count']} 个错误"]
        if not report.suggestions:
            report.suggestions = ["根据执行数据进行针对性优化"]
        if not report.learned:
            report.learned = (
                f"Agent ({agent_role.value}) 完成了一个 {analysis['total_steps']} 步的任务。"
            )

        return report

    def _parse_reflection_response(
        self,
        raw: str,
        task_id: str,
        agent_role: AgentRole,
        success: bool,
    ) -> ReflectionReport:
        """解析 LLM 的反思响应为结构化报告

        从 Markdown 格式的 LLM 输出中提取各章节内容。

        Args:
            raw: LLM 返回的原始文本
            task_id: 任务 ID
            agent_role: Agent 角色
            success: 是否成功

        Returns:
            解析后的 ReflectionReport
        """
        if not raw or not raw.strip():
            return ReflectionReport(
                task_id=task_id,
                agent_id="",
                agent_role=agent_role,
                success=success,
                summary="",
            )

        summary = self._extract_section(raw, "执行总结")
        strengths = self._extract_list_items(raw, "做得好的地方")
        weaknesses = self._extract_list_items(raw, "需要改进的地方")
        suggestions = self._extract_list_items(raw, "改进建议")
        learned = self._extract_section(raw, "学到的东西")

        return ReflectionReport(
            task_id=task_id,
            agent_id="",
            agent_role=agent_role,
            success=success,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            learned=learned,
        )

    # ------------------------------------------------------------------
    # 文本解析工具
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_section(text: str, section_name: str) -> str:
        """提取 Markdown 章节的文本内容

        匹配 ``## 章节名`` 到下一个 ``## `` 或文档结尾之间的内容。

        Args:
            text: Markdown 文本
            section_name: 章节名称

        Returns:
            章节内容（去除首尾空白）
        """
        # 匹配 ## 章节标题，直到下一个 ## 或文档结尾
        pattern = rf"##\s*{re.escape(section_name)}\s*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # 尝试不换行的格式：## 标题 内容
        pattern = rf"##\s*{re.escape(section_name)}\s*(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    @staticmethod
    def _extract_list_items(text: str, section_name: str) -> List[str]:
        """提取 Markdown 章节中的列表项

        支持 ``- item`` / ``* item`` / ``1. item`` 格式。

        Args:
            text: Markdown 文本
            section_name: 章节名称

        Returns:
            列表项字符串列表
        """
        content = ReflectionEngine._extract_section(text, section_name)
        if not content:
            return []

        items = []
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 匹配 - xxx 或 * xxx 格式
            if line.startswith("- ") or line.startswith("* "):
                items.append(line[2:].strip())
            # 匹配 1. xxx 或 1、xxx 格式
            elif re.match(r"^\d+[.、]\s*", line):
                items.append(re.sub(r"^\d+[.、]\s*", "", line).strip())

        return items

    @staticmethod
    def _format_steps_for_prompt(steps: List[AgentStep]) -> str:
        """将步骤列表格式化为提示词可读文本

        Args:
            steps: Agent 执行步骤

        Returns:
            格式化的步骤文本
        """
        if not steps:
            return "（无执行步骤）"

        lines = []
        for i, step in enumerate(steps, 1):
            tool_info = f" [工具: {step.tool_name}]" if step.tool_name else ""
            latency = f" ({step.latency_ms}ms)" if step.latency_ms else ""
            content_preview = step.content[:200].replace("\n", " ")
            lines.append(
                f"{i}. [{step.step_type.value}]{tool_info}{latency}\n"
                f"   {content_preview}"
            )

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 经验提取
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_experience(report: ReflectionReport) -> str:
        """将反思报告转化为可复用的经验文本

        格式化为结构化的 Markdown 文本，适合存入长期记忆。

        Args:
            report: 反思报告

        Returns:
            格式化的经验文本
        """
        lines = [
            f"## 反思经验 [{report.timestamp.strftime('%Y-%m-%d %H:%M')}]",
            f"- 任务ID: {report.task_id}",
            f"- Agent角色: {report.agent_role.value}",
            f"- 执行结果: {'成功' if report.success else '失败'}",
            f"- 总结: {report.summary}",
        ]

        if report.strengths:
            lines.append(f"- 优点: {'; '.join(report.strengths)}")
        if report.weaknesses:
            lines.append(f"- 不足: {'; '.join(report.weaknesses)}")
        if report.suggestions:
            lines.append(f"- 改进建议: {'; '.join(report.suggestions)}")
        if report.learned:
            lines.append(f"- 经验教训: {report.learned}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # 提示词构建
    # ------------------------------------------------------------------

    @staticmethod
    def _build_reflection_prompt(
        task_id: str,
        agent_role: AgentRole,
        success: bool,
        steps_description: str,
        output: str,
        error_message: str = "",
    ) -> str:
        """构建反思提示词

        Args:
            task_id: 任务 ID
            agent_role: Agent 角色
            success: 任务是否成功
            steps_description: 步骤描述文本
            output: 最终输出
            error_message: 错误信息

        Returns:
            格式化的用户提示词
        """
        return f"""请分析以下 Agent 任务执行过程，生成结构化的反思报告。

## 任务信息
- 任务ID: {task_id}
- Agent角色: {agent_role.value}
- 执行结果: {"成功" if success else "失败"}
- 错误信息: {error_message}

## 执行过程
{steps_description}

## 最终输出
{output}

请按以下格式输出反思报告（严格使用 Markdown 标题格式）：

## 执行总结
（简要总结任务执行情况，重点突出关键发现）

## 做得好的地方
- （列出 2-3 个具体的优点或成功经验）

## 需要改进的地方
- （列出 2-3 个具体的不足或问题）

## 改进建议
- （列出 2-3 条针对性的改进建议）

## 学到的东西
（用 1-2 句话总结这次执行学到的最重要的经验）"""
