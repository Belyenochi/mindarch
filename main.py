# mindarch/main.py
import uvicorn
import os
from fastapi import FastAPI
from loguru import logger
from api.app import create_app
from core.config import settings
from db.connection import connect_db, close_db


def serve():
    """启动服务器"""
    app = create_app()
    logger.info(f"启动 MindArch 服务，监听地址: {settings.HOST}:{settings.PORT}")
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS
    )


if __name__ == "__main__":
    serve()
