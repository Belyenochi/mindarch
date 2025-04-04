# api/middleware/auth.py
from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from datetime import datetime, timedelta
from core.config import settings
from services.auth import get_user_by_id


class AuthMiddleware(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)

        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="未提供有效凭证",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None

        token = credentials.credentials

        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
            user_id = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=401,
                    detail="无效的token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            expiration = payload.get("exp")
            if expiration is None:
                raise HTTPException(
                    status_code=401,
                    detail="token没有过期时间",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if datetime.utcnow() > datetime.utcfromtimestamp(expiration):
                raise HTTPException(
                    status_code=401,
                    detail="token已过期",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user = await get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="用户不存在",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            request.state.user = user

            return credentials

        except JWTError:
            raise HTTPException(
                status_code=401,
                detail="无效的token",
                headers={"WWW-Authenticate": "Bearer"},
            )