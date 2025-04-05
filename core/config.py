# core/config.py
from typing import List, Dict, Any, Optional
from pydantic import Field
from pydantic_settings import BaseSettings  # 从这里导入 BaseSettings


class Settings(BaseSettings):
    """系统配置"""

    # API设置
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    WORKERS: int = Field(default=4, env="WORKERS")

    # MongoDB
    MONGODB_URL: str = Field(default="mongodb://localhost:27017/", env="MONGODB_URL")
    MONGODB_DB_NAME: str = Field(default="mindarch", env="MONGODB_DB_NAME")

    # OpenAI (之前是 DeepSeek-R1)
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_API_URL: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_URL")
    OPENAI_MODEL: str = Field(default="gpt-4", env="OPENAI_MODEL")

    # 安全
    SECRET_KEY: str = Field(default="change_this_key_in_production", env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24, env="ACCESS_TOKEN_EXPIRE_MINUTES")  # 1天

    # CORS
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")

    # 文件上传
    UPLOAD_DIR: str = Field(default="./uploads", env="UPLOAD_DIR")
    MAX_UPLOAD_SIZE: int = Field(default=50 * 1024 * 1024, env="MAX_UPLOAD_SIZE")  # 50MB

    # 日志
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: Optional[str] = Field(default="logs/mindarch.log", env="LOG_FILE")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
