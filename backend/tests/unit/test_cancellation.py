"""
取消控制模块测试
"""
import pytest

from agent_forge.core.cancellation import CancellationError, CancellationToken


class TestCancellationToken:
    """测试取消令牌"""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """测试初始状态"""
        token = CancellationToken()
        assert not await token.is_cancelled
        assert await token.reason == ""

    @pytest.mark.asyncio
    async def test_cancel(self):
        """测试取消操作"""
        token = CancellationToken()
        await token.cancel("测试取消")

        assert await token.is_cancelled
        assert await token.reason == "测试取消"

    @pytest.mark.asyncio
    async def test_check_cancellation(self):
        """测试检查取消"""
        token = CancellationToken()
        await token.cancel()

        with pytest.raises(CancellationError):
            await token.check_cancellation()

    @pytest.mark.asyncio
    async def test_check_without_cancel(self):
        """测试未取消时不抛出"""
        token = CancellationToken()
        # 不应抛出异常
        await token.check_cancellation()

    @pytest.mark.asyncio
    async def test_reset(self):
        """测试重置"""
        token = CancellationToken()
        await token.cancel("原因")
        await token.reset()

        assert not await token.is_cancelled
        assert await token.reason == ""
