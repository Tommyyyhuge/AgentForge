"""
AgentForge API Key 管理器

从加密存储中获取并解密 API Key，提供给 LLM 客户端使用。
"""
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database.models import APIKeyORM
from agent_forge.utils.encryption import APIKeyEncryption
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)


class APIKeyManager:
    """API Key 管理器
    
    从数据库加密存储中查询并解密 API Key。
    支持短期内存缓存，请求结束后可清理。
    """
    
    def __init__(self, encryption: APIKeyEncryption):
        self._encryption = encryption
        self._cache: dict[str, str] = {}
    
    async def get_key(
        self,
        provider: str,
        db: AsyncSession,
        user_id: str | None = None,
    ) -> str | None:
        """获取并解密指定 provider 的 API Key
        
        Args:
            provider: 提供商名称（kimi / deepseek）
            db: 数据库会话
            user_id: 可选，限定用户
            
        Returns:
            解密后的 API Key 明文，如果没有则返回 None
        """
        # 1. 检查内存缓存
        cache_key = f"{provider}:{user_id or 'any'}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 2. 查询数据库
        query = select(APIKeyORM).where(
            APIKeyORM.provider == provider,
            APIKeyORM.is_active == True,
            APIKeyORM.permission == "write",
        )
        if user_id:
            query = query.where(APIKeyORM.user_id == user_id)
        
        result = await db.execute(query.order_by(APIKeyORM.created_at.desc()))
        key_record = result.scalars().first()
        
        if not key_record:
            return None
        
        # 3. 解密
        try:
            decrypted = self._encryption.decrypt(key_record.encrypted_key)
        except Exception as e:
            logger.error(f"解密 API Key 失败: {e}")
            return None
        
        # 4. 更新使用统计
        await db.execute(
            update(APIKeyORM)
            .where(APIKeyORM.id == key_record.id)
            .values(
                usage_count=APIKeyORM.usage_count + 1,
                last_used_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        
        # 5. 缓存（短期内存，请求结束清理）
        self._cache[cache_key] = decrypted
        
        return decrypted
    
    async def get_all_keys(
        self,
        db: AsyncSession,
        user_id: str | None = None,
    ) -> dict[str, str]:
        """获取所有可用 provider 的 API Key
        
        Returns:
            {provider_name: decrypted_key, ...}
        """
        providers = ["kimi", "deepseek"]
        result = {}
        
        for provider in providers:
            key = await self.get_key(provider, db, user_id)
            if key:
                result[provider] = key
        
        return result
    
    def clear_cache(self):
        """清空解密缓存"""
        self._cache.clear()
        logger.debug("API Key 缓存已清空")
