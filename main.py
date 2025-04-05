# main.py
import logging
from fastapi import FastAPI
from api.app import create_app

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()


def serve():
    import uvicorn
    try:
        logger.info("启动 MindArch 服务，监听地址: 0.0.0.0:8000")
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        raise


if __name__ == "__main__":
    serve()
