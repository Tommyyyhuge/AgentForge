"""
AgentForge 用户认证 API 路由

提供用户注册、登录和当前用户信息查询。
所有端点前缀: /api/v1/auth
"""
import uuid
from datetime import datetime, timezone

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.database.connection import get_db
from agent_forge.database.models import UserORM
from agent_forge.api.middleware.auth import (
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from agent_forge.models.schemas import Token, UserCreate, LoginRequest, UserResponse
from agent_forge.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["auth"])


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _validate_email(email: str) -> str:
    """验证邮箱格式，返回规范化后的邮箱"""
    try:
        valid = validate_email(email, check_deliverability=False)
        return valid.normalized
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"邮箱格式无效: {str(e)}",
        )


async def _get_user_by_username(
    db: AsyncSession, username: str
) -> UserORM | None:
    """根据用户名查询用户"""
    result = await db.execute(
        select(UserORM).where(UserORM.username == username)
    )
    return result.scalar_one_or_none()


async def _get_user_by_email(
    db: AsyncSession, email: str
) -> UserORM | None:
    """根据邮箱查询用户"""
    result = await db.execute(
        select(UserORM).where(UserORM.email == email)
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# 认证端点
# ---------------------------------------------------------------------------


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """注册新用户

    使用用户名、邮箱和密码创建新账号。
    密码将使用 bcrypt 进行哈希存储。
    """
    # 验证邮箱
    normalized_email = _validate_email(user_data.email)

    # 检查用户名是否已存在
    existing_username = await _get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已被注册",
        )

    # 检查邮箱是否已存在
    existing_email = await _get_user_by_email(db, normalized_email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="邮箱已被注册",
        )

    # 创建用户
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user_data.password)

    user = UserORM(
        id=user_id,
        username=user_data.username,
        email=normalized_email,
        hashed_password=hashed_password,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info(f"新用户注册: {user.username} ({user.email})")

    return user


@router.post(
    "/auth/login",
    response_model=Token,
    summary="用户登录",
)
async def login(user_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录

    使用用户名+密码认证，返回 JWT access token。
    后续请求需在 Authorization 头中携带此 token。
    """
    # 查找用户
    user = await _get_user_by_username(db, user_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 验证密码
    if not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查用户是否活跃
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    # 生成 token
    access_token = create_access_token(data={"sub": user.username})

    logger.info(f"用户登录: {user.username}")

    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
)
async def read_users_me(
    current_user: UserORM = Depends(get_current_active_user),
):
    """获取当前登录用户的信息"""
    return current_user
