# services/auth.py
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel
from jose import jwt, JWTError  # 使用 python-jose 库
import logging

from core.config import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Loaded bcrypt module from: {bcrypt.__file__}")
logger.info(f"bcrypt version: {bcrypt.__version__ if hasattr(bcrypt, '__version__') else 'unknown'}")
logger.info(f"bcrypt has __about__: {hasattr(bcrypt, '__about__')}")
if hasattr(bcrypt, "__about__"):
    logger.info(f"bcrypt __about__.__version__: {bcrypt.__about__.__version__}")

# OAuth2 配置
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """用户模型"""
    id: str
    username: str
    role: str = "user"


class TokenData(BaseModel):
    """令牌数据"""
    sub: str  # 用户ID
    exp: datetime  # 过期时间
    type: str  # 令牌类型（access/refresh）
    role: str  # 用户角色


class AuthService:
    """认证服务"""

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        to_encode = data.copy()

        # 设置过期时间
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        # 添加 JWT 标准字段
        to_encode.update({
            "exp": expire,
            "type": "access"
        })

        # 编码 JWT
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info(f"Created access token for user: {to_encode.get('sub')}, expires at: {expire}")
        return encoded_jwt

    @staticmethod
    async def decode_token(token: str) -> TokenData:
        """解码令牌"""
        try:
            # 解码 JWT
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            logger.debug(f"Decoded token payload: {payload}")

            # 提取必要字段
            sub = payload.get("sub")
            if sub is None:
                logger.warning("Token missing 'sub' field")
                raise HTTPException(status_code=401, detail="无效的令牌")

            exp = payload.get("exp")
            if exp is None:
                logger.warning("Token missing 'exp' field")
                raise HTTPException(status_code=401, detail="令牌没有过期时间")

            # 检查令牌类型
            token_type = payload.get("type", "access")
            if token_type != "access":
                logger.warning(f"Invalid token type: {token_type}")
                raise HTTPException(status_code=401, detail="令牌类型无效")

            # 检查过期时间
            exp_datetime = datetime.fromtimestamp(exp)
            if datetime.utcnow() > exp_datetime:
                logger.warning("Token has expired")
                raise HTTPException(status_code=401, detail="令牌已过期")

            # 提取角色
            role = payload.get("role", "user")

            return TokenData(sub=sub, exp=exp_datetime, type=token_type, role=role)

        except JWTError as e:
            logger.error(f"JWT decode error: {str(e)}")
            raise HTTPException(status_code=401, detail="无效的令牌")


# 用户数据库 (简化的内存存储，实际应用中应使用数据库)
fake_users_db = {
    "admin": {
        "id": "admin",
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),
        "role": "admin"
    },
    "user": {
        "id": "user",
        "username": "user",
        "hashed_password": pwd_context.hash("user"),
        "role": "user"
    }
}


async def get_user_by_username(username: str) -> Optional[User]:
    """根据用户名获取用户"""
    if username in fake_users_db:
        user_data = fake_users_db[username]
        return User(
            id=user_data["id"],
            username=user_data["username"],
            role=user_data["role"]
        )
    return None


async def get_user_by_id(user_id: str) -> Optional[User]:
    """根据用户ID获取用户"""
    for username, user_data in fake_users_db.items():
        if user_data["id"] == user_id:
            return User(
                id=user_data["id"],
                username=user_data["username"],
                role=user_data["role"]
            )
    return None


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = await get_user_by_username(username)
    if not user:
        logger.warning(f"User not found: {username}")
        return None

    user_data = fake_users_db[username]
    if not AuthService.verify_password(password, user_data["hashed_password"]):
        logger.warning(f"Invalid password for user: {username}")
        return None

    logger.info(f"User authenticated successfully: {username}")
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户"""
    token_data = await AuthService.decode_token(token)

    user = await get_user_by_id(token_data.sub)
    if user is None:
        logger.warning(f"User not found for ID: {token_data.sub}")
        raise HTTPException(status_code=401, detail="用户不存在")

    logger.info(f"Current user retrieved: {user.username}")
    return user