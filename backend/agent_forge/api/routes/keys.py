"""
AgentForge API Key 管理路由

提供 API Key 的增删查操作。
所有端点前缀: /api/v1/keys
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from agent_forge.api.middleware.auth import get_current_active_user
from agent_forge.api.responses import success_response
from agent_forge.config.settings import settings
from agent_forge.core.providers import ProviderRegistry
from agent_forge.database.connection import get_db
from agent_forge.database.models import APIKeyORM, UserORM
from agent_forge.utils.encryption import APIKeyEncryption
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/keys", tags=["keys"])
provider_registry = ProviderRegistry()


# ============================================================
# 请求/响应模型
# ============================================================

class CreateKeyRequest(BaseModel):
    provider: str = Field(..., description="Provider type or preset alias")
    api_key: str = Field(..., min_length=8, description="API Key 明文")
    permission: str = Field(default="write", description="权限：read / write / admin")


class LinkedProviderConfigResponse(BaseModel):
    id: str
    display_name: str
    provider_type: str


class KeyResponse(BaseModel):
    id: str
    provider: str
    masked_key: str
    permission: str
    usage_count: int = 0
    is_active: bool = True
    created_at: str
    linked_provider_config_count: int = 0
    linked_provider_configs: list[LinkedProviderConfigResponse] = Field(
        default_factory=list
    )


class KeyUsageResponse(BaseModel):
    id: str
    provider: str
    masked_key: str
    usage_count: int
    last_used_at: str | None


# ============================================================
# 辅助函数
# ============================================================

def _get_encryption() -> APIKeyEncryption:
    """获取加密管理器实例"""
    return APIKeyEncryption(
        master_key=settings.ENCRYPTION_KEY.get_secret_value(),
        salt=settings.ENCRYPTION_SALT.get_secret_value(),
    )


def _provider_values(provider: str) -> set[str]:
    normalized = provider.strip().lower()
    for preset in provider_registry.list_presets():
        values = {preset.provider_type.value, *preset.aliases}
        if normalized in values:
            return values
    raise HTTPException(
        status_code=400,
        detail="Unsupported Provider.",
    )


def _validate_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    _provider_values(normalized)
    return normalized


def _linked_provider_configs(key: APIKeyORM) -> list[LinkedProviderConfigResponse]:
    return [
        LinkedProviderConfigResponse(
            id=config.id,
            display_name=config.display_name,
            provider_type=config.provider_type,
        )
        for config in getattr(key, "provider_configs", [])
        if config.is_active
    ]


def _orm_to_response(key: APIKeyORM) -> KeyResponse:
    """将 ORM 模型转换为响应模型"""
    linked_configs = _linked_provider_configs(key)
    return KeyResponse(
        id=key.id,
        provider=key.provider,
        masked_key=key.masked_key,
        permission=key.permission,
        usage_count=key.usage_count,
        is_active=key.is_active,
        created_at=key.created_at.isoformat() if key.created_at else "",
        linked_provider_config_count=len(linked_configs),
        linked_provider_configs=linked_configs,
    )


# ============================================================
# API 端点
# ============================================================

@router.post(
    "",
    response_model=None,
    status_code=status.HTTP_201_CREATED,
    summary="添加 API Key",
)
async def create_key(
    request: CreateKeyRequest,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """添加 API Key — 传入明文，加密后存储"""
    provider = _validate_provider(request.provider)
    encryption = _get_encryption()

    # 加密
    encrypted = encryption.encrypt(request.api_key)
    masked = APIKeyEncryption.mask_key(request.api_key)

    # 存储
    key = APIKeyORM(
        id=str(uuid.uuid4()),
        user_id=user.id,
        provider=provider,
        encrypted_key=encrypted,
        masked_key=masked,
        permission=request.permission,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)

    logger.info(f"用户 {user.username} 添加了 {provider} API Key: {masked}")
    return success_response(_orm_to_response(key))


@router.get(
    "",
    response_model=None,
    summary="列出 API Key",
)
async def list_keys(
    provider: str | None = None,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """列出当前用户的所有 API Key（只返回 masked_key）"""
    query = (
        select(APIKeyORM)
        .options(selectinload(APIKeyORM.provider_configs))
        .where(
            APIKeyORM.user_id == user.id,
            APIKeyORM.is_active.is_(True),
        )
    )
    if provider:
        query = query.where(APIKeyORM.provider.in_(_provider_values(provider)))

    result = await db.execute(
        query.order_by(APIKeyORM.created_at.desc())
    )
    keys = result.scalars().all()
    return success_response([_orm_to_response(k) for k in keys])


@router.get(
    "/{key_id}",
    response_model=None,
    summary="获取 Key 详情",
)
async def get_key(
    key_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个 API Key 详情"""
    result = await db.execute(
        select(APIKeyORM).options(selectinload(APIKeyORM.provider_configs)).where(
            APIKeyORM.id == key_id,
            APIKeyORM.user_id == user.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key 未找到")
    return success_response(_orm_to_response(key))


@router.get(
    "/{key_id}/usage",
    response_model=None,
    summary="获取 Key 使用统计",
)
async def get_key_usage(
    key_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """获取指定 Key 的使用统计"""
    result = await db.execute(
        select(APIKeyORM).options(selectinload(APIKeyORM.provider_configs)).where(
            APIKeyORM.id == key_id,
            APIKeyORM.user_id == user.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key 未找到")

    return success_response(
        KeyUsageResponse(
            id=key.id,
            provider=key.provider,
            masked_key=key.masked_key,
            usage_count=key.usage_count,
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_200_OK,
    summary="删除 API Key",
)
async def delete_key(
    key_id: str,
    user: UserORM = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """删除 API Key（软删除，设置 is_active=False）"""
    result = await db.execute(
        select(APIKeyORM).options(selectinload(APIKeyORM.provider_configs)).where(
            APIKeyORM.id == key_id,
            APIKeyORM.user_id == user.id,
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key 未找到")

    linked_configs = _linked_provider_configs(key)
    key.is_active = False
    await db.commit()

    logger.info(f"用户 {user.username} 删除了 {key.provider} API Key: {key.masked_key}")
    return success_response(
        {
            "id": key_id,
            "linked_provider_config_count": len(linked_configs),
            "linked_provider_configs": linked_configs,
        },
        message=(
            "Key deleted. Linked Provider config calls will fail until a new "
            "active API Key is assigned."
            if linked_configs
            else "Key 已删除"
        ),
    )
