# db/repositories/knowledge_unit_repo.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson.objectid import ObjectId

from core.models.knowledge_unit import KnowledgeUnit
from db.connection import get_database


class KnowledgeUnitRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db[KnowledgeUnit.Settings.name]

    async def create(self, unit: KnowledgeUnit) -> KnowledgeUnit:
        """创建新的知识单元"""
        result = await unit.insert()
        return result

    async def get_by_id(self, unit_id: str) -> Optional[KnowledgeUnit]:
        """通过ID获取知识单元"""
        try:
            return await KnowledgeUnit.get(ObjectId(unit_id))
        except:
            return None

    async def find_one(self, query: Dict[str, Any]) -> Optional[KnowledgeUnit]:
        """查找单个知识单元"""
        return await KnowledgeUnit.find_one(query)

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[KnowledgeUnit]:
        """查找多个知识单元"""
        find_query = KnowledgeUnit.find(query)

        if sort:
            find_query = find_query.sort(sort)
        else:
            find_query = find_query.sort([("created_at", -1)])

        return await find_query.skip(skip).limit(limit).to_list()

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await KnowledgeUnit.find(query).count()

    async def update(self, unit_id: str, data: Dict[str, Any]):
        """更新知识单元"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(unit_id)},
                {"$set": {**data, "updated_at": datetime.now()}}
            )
            return result
        except Exception as e:
            raise Exception(f"更新知识单元失败: {str(e)}")

    async def delete(self, unit_id: str):
        """删除知识单元"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(unit_id)})
            return result
        except Exception as e:
            raise Exception(f"删除知识单元失败: {str(e)}")

    async def increment_view_count(self, unit_id: str):
        """增加查看计数"""
        try:
            await self.collection.update_one(
                {"_id": ObjectId(unit_id)},
                {"$inc": {"metrics.view_count": 1}}
            )
        except:
            pass  # 忽略计数错误

    async def search(self, text_query: str, filters: Optional[Dict[str, Any]] = None,
                     limit: int = 20, skip: int = 0) -> List[KnowledgeUnit]:
        """全文搜索知识单元"""
        query = {"$text": {"$search": text_query}}

        if filters:
            query.update(filters)

        find_query = KnowledgeUnit.find(
            query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])

        return await find_query.skip(skip).limit(limit).to_list()

    async def count_search(self, text_query: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """计数搜索结果"""
        query = {"$text": {"$search": text_query}}

        if filters:
            query.update(filters)

        return await KnowledgeUnit.find(query).count()

    async def bulk_insert(self, units: List[KnowledgeUnit]) -> List[KnowledgeUnit]:
        """批量插入知识单元"""
        if not units:
            return []

        result = await KnowledgeUnit.insert_many(units)
        return result