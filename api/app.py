# api/app.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from core.config import settings
from api.routes import knowledge_units, semantic_triples, knowledge_graphs, file_imports
from api.middleware.auth import AuthMiddleware
from db.connection import connect_db, close_db


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="MindArch API",
        description="知识图谱管理系统API",
        version="0.1.0",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册事件处理器
    app.add_event_handler("startup", connect_db)
    app.add_event_handler("shutdown", close_db)

    # 注册路由
    app.include_router(knowledge_units.router, prefix=settings.API_V1_STR)
    app.include_router(semantic_triples.router, prefix=settings.API_V1_STR)
    app.include_router(knowledge_graphs.router, prefix=settings.API_V1_STR)
    app.include_router(file_imports.router, prefix=settings.API_V1_STR)

    # 全局异常处理
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"全局异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后再试。"}
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    # 健康检查端点
    @app.get("/health", tags=["系统"])
    async def health_check():
        return {"status": "healthy"}

    return app