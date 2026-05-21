"""
AgentForge JWT 认证依赖模块

提供 JWT token 创建、验证和用户认证的依赖注入函数。
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_forge.config.settings import settings
from agent_forge.database.connection import get_db
from agent_forge.database.models import UserORM
from agent_forge.models.schemas import TokenData

# ---------------------------------------------------------------------------
# 密码哈希（使用 bcrypt 替代 passlib，避免与新版 bcrypt 不兼容）
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """对明文密码进行 bcrypt 哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# ---------------------------------------------------------------------------
# JWT Token
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT access token

    Args:
        data: 需要编码到 token 中的数据（必须包含 "sub" 键）
        expires_delta: 过期时间差（默认使用 settings.JWT_EXPIRE_DAYS）

    Returns:
        编码后的 JWT token 字符串
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.JWT_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire})
    secret = settings.JWT_SECRET_KEY.get_secret_value()
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserORM:
    """从 JWT token 中解析当前用户

    验证 token 有效性，从数据库查找对应的用户。

    Raises:
        HTTPException 401: token 无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        secret = settings.JWT_SECRET_KEY.get_secret_value()
        payload = jwt.decode(
            token, secret, algorithms=[settings.JWT_ALGORITHM]
        )
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # 从数据库查找用户
    result = await db.execute(
        select(UserORM).where(UserORM.username == token_data.username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: UserORM = Depends(get_current_user),
) -> UserORM:
    """检查当前用户是否活跃

    Raises:
        HTTPException 400: 用户已被禁用
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已被禁用",
        )
    return current_user
