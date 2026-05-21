"""
AgentForge 任务取消控制模块
"""
import asyncio


class CancellationError(Exception):
    """取消错误异常"""

    pass


class CancellationToken:
    """取消令牌类

    用于控制长时间运行任务的取消操作。
    任务执行过程中定期检查此令牌，如果已取消则抛出 CancellationError。

    注意：cancel() 和 check_cancellation() 是 async 方法，
    需要在异步上下文中调用。
    """

    def __init__(self):
        self._cancelled = False
        self._reason: str = ""
        self._lock = asyncio.Lock()

    @property
    async def is_cancelled(self) -> bool:
        """检查是否已取消"""
        async with self._lock:
            return self._cancelled

    @property
    async def reason(self) -> str:
        """获取取消原因"""
        async with self._lock:
            return self._reason

    async def cancel(self, reason: str = "用户取消"):
        """取消任务

        Args:
            reason: 取消原因
        """
        async with self._lock:
            self._cancelled = True
            self._reason = reason

    async def check_cancellation(self):
        """检查取消状态，如果已取消则抛出异常

        在任务的执行循环中定期调用此方法。
        """
        async with self._lock:
            if self._cancelled:
                raise CancellationError(f"任务已取消: {self._reason}")

    async def reset(self):
        """重置取消状态"""
        async with self._lock:
            self._cancelled = False
            self._reason = ""
