# db/connection.py
import motor.motor_asyncio
from beanie import init_beanie
from loguru import logger

from core.config import settings
from core.models.knowledge_unit import KnowledgeUnit
from core.models.semantic_triple import SemanticTriple
from core.models.knowledge_graph import KnowledgeGraph

# 全局客户端和数据库对象
client = None
db = None


async def connect_db():
    """连接到MongoDB并初始化Beanie"""
    global client, db

    try:
        # 创建Motor客户端
        client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGODB_URL)
        db = client[settings.MONGODB_DB_NAME]

        # 初始化Beanie
        await init_beanie(
            database=db,
            document_models=[
                KnowledgeUnit,
                SemanticTriple,
                KnowledgeGraph,
            ]
        )

        logger.info("已连接到MongoDB")
    except Exception as e:
        logger.error(f"连接MongoDB失败: {str(e)}")
        raise


async def close_db():
    """关闭MongoDB连接"""
    global client
    if client:
        client.close()
        logger.info("MongoDB连接已关闭")


def get_database():
    """获取数据库实例"""
    global db
    if not db:
        raise RuntimeError("数据库连接未初始化")
    return db