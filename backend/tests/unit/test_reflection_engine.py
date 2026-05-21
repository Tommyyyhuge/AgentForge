"""
反思引擎模块测试

测试 ReflectionEngine 的以下功能：
- 步骤分析统计
- LLM 反思报告生成与解析
- 经验提取与长期记忆存储
- Agent 经验总结检索
- 反思过程异常不影响主流程
- 默认报告生成（LLM 失败时降级）
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_forge.core.llm_client import LLMResponse
from agent_forge.core.memory_manager import MemoryManager
from agent_forge.core.reflection_engine import ReflectionEngine, ReflectionReport
from agent_forge.models.schemas import AgentRole, AgentStep, StepType, TaskResult, TaskStatus


# =============================================================================
# 工厂函数
# =============================================================================


def _make_step(
    step_type: StepType,
    step_number: int = 1,
    task_id: str = "task-1",
    agent_id: str = "agent-1",
    agent_role: AgentRole = AgentRole.EXECUTOR,
    content: str = "test",
    tool_name: str | None = None,
    latency_ms: int | None = None,
) -> AgentStep:
    """创建 AgentStep 实例用于测试"""
    return AgentStep(
        task_id=task_id,
        agent_id=agent_id,
        agent_role=agent_role,
        step_number=step_number,
        step_type=step_type,
        content=content,
        tool_name=tool_name,
        latency_ms=latency_ms,
    )


def _make_result(
    status: TaskStatus = TaskStatus.COMPLETED,
    task_id: str = "task-1",
    output: str = "任务完成",
    error_message: str | None = None,
    steps_count: int = 5,
) -> TaskResult:
    """创建 TaskResult 实例用于测试"""
    return TaskResult(
        task_id=task_id,
        status=status,
        output=output,
        error_message=error_message,
        steps_count=steps_count,
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_llm_router():
    """模拟 LLMRouter 实例"""
    router = AsyncMock()
    router.chat = AsyncMock(return_value=LLMResponse(
        content="""
## 执行总结
任务顺利完成，Agent 按计划执行了所有步骤。

## 做得好的地方
- 代码质量高
- 错误处理完善

## 需要改进的地方
- 执行速度偏慢
- 日志不够详细

## 改进建议
- 优化关键路径性能
- 增加详细日志记录

## 学到的东西
在执行复杂任务时应该先分解再执行。
""",
        model="mock-model",
        usage={"total_tokens": 200},
        latency_ms=100,
    ))
    return router


@pytest.fixture
def mock_memory_manager():
    """模拟 MemoryManager 实例"""
    mm = AsyncMock(spec=MemoryManager)
    mm.add_long_term = AsyncMock()
    mm.search_long_term = AsyncMock(return_value=[
        MagicMock(content="## 反思经验 [2026-01-01]\n- 经验1"),
        MagicMock(content="## 反思经验 [2026-01-02]\n- 经验2"),
    ])
    return mm


@pytest.fixture
def engine(mock_llm_router, mock_memory_manager):
    """提供 ReflectionEngine 实例"""
    return ReflectionEngine(
        llm_router=mock_llm_router,
        memory_manager=mock_memory_manager,
    )


@pytest.fixture
def engine_no_memory(mock_llm_router):
    """不配置 MemoryManager 的引擎"""
    return ReflectionEngine(llm_router=mock_llm_router)


@pytest.fixture
def sample_steps():
    """示例执行步骤"""
    return [
        _make_step(StepType.THOUGHT, step_number=1, content="分析需求", latency_ms=100),
        _make_step(StepType.ACTION, step_number=2, content="编写代码", tool_name="write_file", latency_ms=500),
        _make_step(StepType.OBSERVATION, step_number=3, content="代码检查通过", latency_ms=50),
        _make_step(StepType.ACTION, step_number=4, content="运行测试", tool_name="run_tests", latency_ms=1000),
        _make_step(StepType.FINAL, step_number=5, content="任务完成", latency_ms=30),
    ]


# =============================================================================
# 测试: 步骤分析
# =============================================================================


class TestAnalyzeSteps:
    """测试步骤分析统计功能"""

    def test_empty_steps(self, engine):
        """空步骤列表"""
        analysis = engine._analyze_steps([])
        assert analysis["total_steps"] == 0
        assert analysis["thought_count"] == 0
        assert analysis["action_count"] == 0
        assert analysis["avg_latency_ms"] == 0

    def test_mixed_steps(self, engine, sample_steps):
        """混合步骤类型"""
        analysis = engine._analyze_steps(sample_steps)
        assert analysis["total_steps"] == 5
        assert analysis["thought_count"] == 1
        assert analysis["action_count"] == 2
        assert analysis["observation_count"] == 1
        assert analysis["final_count"] == 1
        assert analysis["error_count"] == 0
        assert analysis["tool_call_count"] == 2  # write_file, run_tests

    def test_latency_calculation(self, engine, sample_steps):
        """耗时计算"""
        analysis = engine._analyze_steps(sample_steps)
        assert analysis["total_latency_ms"] == 1680  # 100+500+50+1000+30
        assert analysis["avg_latency_ms"] == 336.0  # 1680 / 5

    def test_no_latency_steps(self, engine):
        """无耗时信息的步骤"""
        steps = [
            _make_step(StepType.THOUGHT, step_number=1),
            _make_step(StepType.ACTION, step_number=2, tool_name="test"),
        ]
        analysis = engine._analyze_steps(steps)
        assert analysis["total_latency_ms"] == 0
        assert analysis["avg_latency_ms"] == 0

    def test_all_types(self, engine):
        """覆盖所有 StepType"""
        steps = [
            _make_step(StepType.THOUGHT, step_number=1),
            _make_step(StepType.ACTION, step_number=2),
            _make_step(StepType.OBSERVATION, step_number=3),
            _make_step(StepType.ERROR, step_number=4),
            _make_step(StepType.FINAL, step_number=5),
        ]
        analysis = engine._analyze_steps(steps)
        assert analysis["thought_count"] == 1
        assert analysis["action_count"] == 1
        assert analysis["observation_count"] == 1
        assert analysis["error_count"] == 1
        assert analysis["final_count"] == 1


# =============================================================================
# 测试: 反思报告生成
# =============================================================================


class TestReflect:
    """测试完整的反思流程"""

    @pytest.mark.asyncio
    async def test_basic_reflection(self, engine, sample_steps):
        """基本反思流程"""
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=sample_steps,
            result=result,
        )

        assert isinstance(report, ReflectionReport)
        assert report.task_id == "task-1"
        assert report.agent_id == "agent-1"
        assert report.agent_role == AgentRole.CODER
        assert report.success is True
        assert report.summary != ""
        assert len(report.strengths) > 0
        assert len(report.weaknesses) > 0
        assert len(report.suggestions) > 0
        assert report.learned != ""

    @pytest.mark.asyncio
    async def test_reflection_failed_task(self, engine, sample_steps):
        """失败任务的反思"""
        result = _make_result(
            status=TaskStatus.FAILED,
            output="执行中断",
            error_message="运行时异常: 文件未找到",
        )
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=sample_steps,
            result=result,
        )
        assert report.success is False
        assert report.summary != ""

    @pytest.mark.asyncio
    async def test_reflection_empty_steps(self, engine):
        """空步骤列表的反思"""
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.EXECUTOR,
            steps=[],
            result=result,
        )
        assert isinstance(report, ReflectionReport)
        assert report.summary != ""

    @pytest.mark.asyncio
    async def test_llm_call_failure(self, engine, sample_steps):
        """LLM 调用失败时使用默认报告"""
        engine.llm_router.chat = AsyncMock(side_effect=Exception("LLM 服务不可用"))
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=sample_steps,
            result=result,
        )
        # LLM 失败时应有默认值
        assert isinstance(report, ReflectionReport)
        assert report.summary != ""
        assert "顺利完成" in report.summary or "执行" in report.summary

    @pytest.mark.asyncio
    async def test_experience_stored_to_memory(self, engine, sample_steps):
        """经验应自动存入长期记忆"""
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=sample_steps,
            result=result,
        )
        # 验证报告和 add_long_term 被调用
        assert report is not None
        engine.memory_manager.add_long_term.assert_called_once()
        call_kwargs = engine.memory_manager.add_long_term.call_args.kwargs
        assert call_kwargs["agent_id"] == "agent-1"
        assert call_kwargs["agent_role"] == "coder"
        assert call_kwargs["task_id"] == "task-1"
        assert call_kwargs["metadata"]["type"] == "reflection"
        assert "反思经验" in call_kwargs["content"]

    @pytest.mark.asyncio
    async def test_no_memory_manager(self, engine_no_memory, sample_steps):
        """不配置 MemoryManager 时不应报错"""
        result = _make_result()
        report = await engine_no_memory.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.EXECUTOR,
            steps=sample_steps,
            result=result,
        )
        assert isinstance(report, ReflectionReport)
        assert report.summary != ""

    @pytest.mark.asyncio
    async def test_memory_store_failure(self, engine, sample_steps):
        """长期记忆存储失败不应影响反思"""
        engine.memory_manager.add_long_term = AsyncMock(
            side_effect=Exception("存储失败")
        )
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=sample_steps,
            result=result,
        )
        # 即使存储失败，反思报告也应正常返回
        assert isinstance(report, ReflectionReport)
        assert report.summary != ""


# =============================================================================
# 测试: 报告解析
# =============================================================================


class TestParseResponse:
    """测试 LLM 响应解析"""

    def test_parse_full_response(self, engine):
        """完整响应的解析"""
        raw = """
## 执行总结
任务完成良好

## 做得好的地方
- 效率高
- 质量好
- 错误少

## 需要改进的地方
- 速度可优化
- 文档需补充

## 改进建议
- 使用缓存
- 增加注释

## 学到的东西
先规划后执行可以提高效率
"""
        report = engine._parse_reflection_response(raw, "task-1", AgentRole.CODER, True)
        assert report.summary == "任务完成良好"
        assert len(report.strengths) == 3
        assert "效率高" in report.strengths
        assert len(report.weaknesses) == 2
        assert "速度可优化" in report.weaknesses
        assert len(report.suggestions) == 2
        assert "使用缓存" in report.suggestions
        assert "先规划后执行" in report.learned

    def test_parse_empty_response(self, engine):
        """空响应"""
        report = engine._parse_reflection_response("", "task-1", AgentRole.EXECUTOR, True)
        assert report.summary == ""

    def test_parse_malformed_response(self, engine):
        """格式不完整的响应"""
        raw = "这是一段没有格式的文本"
        report = engine._parse_reflection_response(raw, "task-1", AgentRole.EXECUTOR, False)
        # 应该返回空字段的报告
        assert report.summary == ""

    def test_parse_partial_response(self, engine):
        """部分章节缺失"""
        raw = """
## 执行总结
只完成了部分工作

## 做得好的地方
- 工作态度积极
"""
        report = engine._parse_reflection_response(raw, "task-1", AgentRole.EXECUTOR, True)
        assert report.summary == "只完成了部分工作"
        assert len(report.strengths) == 1
        assert len(report.weaknesses) == 0  # 缺失章节
        assert len(report.suggestions) == 0
        assert report.learned == ""

    def test_parse_numbered_list(self, engine):
        """带编号的列表项"""
        raw = """
## 做得好的地方
1. 性能指标达标
2. 代码风格规范
"""
        items = engine._extract_list_items(raw, "做得好的地方")
        assert len(items) == 2
        assert "性能指标达标" in items
        assert "代码风格规范" in items


# =============================================================================
# 测试: 经验提取
# =============================================================================


class TestExtractExperience:
    """测试经验提取"""

    def test_format_experience(self):
        """经验文本格式"""
        report = ReflectionReport(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            success=True,
            summary="任务完成",
            strengths=["效率高", "质量好"],
            weaknesses=["速度慢"],
            suggestions=["优化性能"],
            learned="先规划再执行",
        )
        text = ReflectionEngine._extract_experience(report)
        assert "反思经验" in text
        assert "任务-1" in text or "task-1" in text
        assert "效率高" in text
        assert "优化性能" in text
        assert "先规划再执行" in text

    def test_experience_with_empty_fields(self):
        """空字段的处理"""
        report = ReflectionReport(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.EXECUTOR,
            success=False,
            summary="失败",
        )
        text = ReflectionEngine._extract_experience(report)
        # 不应出现空字段的标记
        assert "优点" not in text
        assert "不足" not in text


# =============================================================================
# 测试: Agent 经验检索
# =============================================================================


class TestGetInsights:
    """测试经验总结检索"""

    @pytest.mark.asyncio
    async def test_get_insights(self, engine):
        """获取经验总结"""
        insights = await engine.get_agent_insights(AgentRole.CODER, limit=5)
        assert len(insights) == 2
        engine.memory_manager.search_long_term.assert_called_once_with(
            query="反思经验",
            limit=5,
            agent_role="coder",
        )

    @pytest.mark.asyncio
    async def test_get_insights_no_memory(self, engine_no_memory):
        """未配置记忆管理器时返回空列表"""
        insights = await engine_no_memory.get_agent_insights(AgentRole.EXECUTOR)
        assert insights == []

    @pytest.mark.asyncio
    async def test_get_insights_search_failure(self, engine):
        """搜索失败时返回空列表"""
        engine.memory_manager.search_long_term = AsyncMock(
            side_effect=Exception("搜索失败")
        )
        insights = await engine.get_agent_insights(AgentRole.CODER)
        assert insights == []


# =============================================================================
# 测试: ReflectionReport 序列化
# =============================================================================


class TestReflectionReportSerialization:
    """测试 ReflectionReport 序列化/反序列化"""

    def test_to_dict(self):
        """序列化"""
        report = ReflectionReport(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            success=True,
            summary="好",
            strengths=["a"],
            weaknesses=["b"],
            suggestions=["c"],
            learned="d",
        )
        data = report.to_dict()
        assert data["task_id"] == "task-1"
        assert data["agent_role"] == "coder"
        assert data["success"] is True
        assert data["strengths"] == ["a"]

    def test_from_dict(self):
        """反序列化"""
        data = {
            "task_id": "task-1",
            "agent_id": "agent-1",
            "agent_role": "coder",
            "success": True,
            "summary": "好",
            "strengths": ["a"],
            "weaknesses": ["b"],
            "suggestions": ["c"],
            "learned": "d",
            "timestamp": "2026-01-01T00:00:00+00:00",
        }
        report = ReflectionReport.from_dict(data)
        assert report.task_id == "task-1"
        assert report.agent_role == AgentRole.CODER
        assert report.strengths == ["a"]


# =============================================================================
# 测试: 步骤格式化
# =============================================================================


class TestFormatSteps:
    """测试步骤格式化功能"""

    def test_empty(self):
        """空列表"""
        result = ReflectionEngine._format_steps_for_prompt([])
        assert result == "（无执行步骤）"

    def test_single_step(self):
        """单步骤"""
        step = _make_step(StepType.THOUGHT, step_number=1, content="思考中")
        result = ReflectionEngine._format_steps_for_prompt([step])
        assert "思考中" in result
        assert "[thought]" in result

    def test_tool_and_latency(self):
        """工具名和耗时"""
        step = _make_step(
            StepType.ACTION, step_number=1,
            content="执行操作", tool_name="search",
            latency_ms=200,
        )
        result = ReflectionEngine._format_steps_for_prompt([step])
        assert "[工具: search]" in result
        assert "(200ms)" in result


# =============================================================================
# 测试: 默认报告生成（LLM 失败降级）
# =============================================================================


class TestDefaultReport:
    """测试 LLM 失败时的默认报告"""

    @pytest.mark.asyncio
    async def test_default_report_success(self, engine):
        """成功任务的默认报告"""
        # 模拟 LLM 返回空内容
        engine.llm_router.chat = AsyncMock(return_value=LLMResponse(
            content="", model="mock", usage={}, latency_ms=0,
        ))
        result = _make_result()
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=[
                _make_step(StepType.THOUGHT, step_number=1),
                _make_step(StepType.FINAL, step_number=2),
            ],
            result=result,
        )
        # 应有默认值
        assert report.summary != ""
        assert "顺利完成" in report.summary
        assert len(report.strengths) == 1
        assert report.strengths[0] == "任务顺利完成"

    @pytest.mark.asyncio
    async def test_default_report_failure(self, engine):
        """失败任务的默认报告"""
        engine.llm_router.chat = AsyncMock(return_value=LLMResponse(
            content="", model="mock", usage={}, latency_ms=0,
        ))
        result = _make_result(
            status=TaskStatus.FAILED,
            error_message="运行时异常",
        )
        report = await engine.reflect(
            task_id="task-1",
            agent_id="agent-1",
            agent_role=AgentRole.CODER,
            steps=[
                _make_step(StepType.ERROR, step_number=1, content="出错了"),
            ],
            result=result,
        )
        assert report.success is False
        # 有错误步骤时应有对应的 weakness
        assert len(report.weaknesses) > 0
        assert "错误" in report.weaknesses[0]


# =============================================================================
# 测试: 提示词构建
# =============================================================================


class TestBuildPrompt:
    """测试提示词构建"""

    def test_prompt_contains_key_info(self):
        """提示词包含关键信息"""
        prompt = ReflectionEngine._build_reflection_prompt(
            task_id="task-1",
            agent_role=AgentRole.CODER,
            success=True,
            steps_description="步骤详情",
            output="完成",
            error_message="无",
        )
        assert "task-1" in prompt
        assert "coder" in prompt or "CODER" in prompt
        assert "成功" in prompt
        assert "步骤详情" in prompt
        assert "完成" in prompt
        assert "执行总结" in prompt
        assert "做得好的地方" in prompt
        assert "需要改进的地方" in prompt
        assert "改进建议" in prompt
        assert "学到的东西" in prompt

    def test_prompt_failure(self):
        """失败任务的提示词"""
        prompt = ReflectionEngine._build_reflection_prompt(
            task_id="task-1",
            agent_role=AgentRole.CODER,
            success=False,
            steps_description="步骤",
            output="失败",
            error_message="错误信息",
        )
        assert "失败" in prompt
        assert "错误信息" in prompt
