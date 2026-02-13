"""
认证工具函数 - JWT 和密码处理
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from pydantic_settings import BaseSettings


# ==================== 配置 ====================
class AuthSettings(BaseSettings):
    """认证配置"""
    jwt_secret_key: str = "your-secret-key-change-this-in-production-min-32-chars"
    access_token_expire_days: int = 7

    class Config:
        env_file = ".env"
        env_prefix = ""  # JWT_SECRET_KEY（无前缀）
        extra = "ignore"  # 忽略额外的环境变量


auth_settings = AuthSettings()

# JWT 配置（从环境变量读取）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", auth_settings.jwt_secret_key)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = auth_settings.access_token_expire_days

# 密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


# ==================== Pydantic 模型 ====================
class Token(BaseModel):
    """JWT Token 响应"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 数据"""
    user_id: Optional[int] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    """用户登录请求"""
    email: str
    password: str


class UserRegister(BaseModel):
    """用户注册请求"""
    email: str
    password: str
    confirm_password: str  # 确认密码


# ==================== 密码处理 ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    验证密码强度

    要求：
    - 至少8个字符
    - 包含字母和数字

    Args:
        password: 密码

    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    if len(password) < 8:
        return False, "密码长度至少8个字符"

    if not any(c.isalpha() for c in password):
        return False, "密码必须包含字母"

    if not any(c.isdigit() for c in password):
        return False, "密码必须包含数字"

    return True, ""


# ==================== JWT Token 处理 ====================
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT access token

    Args:
        data: 要编码的数据（通常是 {"sub": user_id, "email": email}）
        expires_delta: 过期时间增量

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    # 确保 sub 是字符串（JWT 标准）
    if "sub" in to_encode and isinstance(to_encode["sub"], int):
        to_encode["sub"] = str(to_encode["sub"])

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> TokenData:
    """
    解码 JWT token

    Args:
        token: JWT token

    Returns:
        TokenData: 解码后的数据

    Raises:
        HTTPException: Token 无效或过期
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None or email is None:
            raise credentials_exception

        # 转换 user_id 为整数（可能是字符串）
        if isinstance(user_id, str):
            user_id = int(user_id)

        return TokenData(user_id=user_id, email=email)

    except (JWTError, ValueError):
        raise credentials_exception


# ==================== 依赖注入 ====================
def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """
    获取当前登录用户（依赖注入）

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        TokenData: 当前用户的数据

    Raises:
        HTTPException: 未认证
    """
    token = credentials.credentials
    return decode_access_token(token)


# ==================== 辅助函数 ====================
def validate_email(email: str) -> tuple[bool, str]:
    """
    验证邮箱格式

    Args:
        email: 邮箱地址

    Returns:
        tuple[bool, str]: (是否有效, 错误信息)
    """
    import re

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "邮箱格式不正确"

    return True, ""
