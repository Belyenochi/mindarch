# services/auth.py
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel

from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """用户模型"""
    id: str
    username: str
    email: Optional[str] = None
    role: str = "user"


class TokenData(BaseModel):
    """令牌数据"""
    sub: str
    exp: datetime
    type: str
    role: str


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

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    async def decode_token(token: str) -> TokenData:
        """解码令牌"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

            sub = payload.get("sub")
            if sub is None:
                raise HTTPException(status_code=401, detail="无效的令牌")

            exp = payload.get("exp")
            if exp is None:
                raise HTTPException(status_code=401, detail="令牌没有过期时间")

            token_type = payload.get("type", "access")
            role = payload.get("role", "user")

            return TokenData(sub=sub, exp=datetime.fromtimestamp(exp), type=token_type, role=role)

        except JWTError:
            raise HTTPException(status_code=401, detail="无效的令牌")


# 用户数据库 (简化的内存存储，实际应用中应使用数据库)
fake_users_db = {
    "admin": {
        "id": "admin",
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": pwd_context.hash("admin"),
        "role": "admin"
    },
    "user": {
        "id": "user",
        "username": "user",
        "email": "user@example.com",
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
            email=user_data["email"],
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
                email=user_data["email"],
                role=user_data["role"]
            )
    return None


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """验证用户"""
    user = await get_user_by_username(username)
    if not user:
        return None

    user_data = fake_users_db[username]
    if not AuthService.verify_password(password, user_data["hashed_password"]):
        return None

    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """获取当前用户"""
    token_data = await AuthService.decode_token(token)

    user = await get_user_by_id(token_data.sub)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")

    return user