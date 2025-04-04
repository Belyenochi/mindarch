# db/repositories/semantic_triple_repo.py
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson.objectid import ObjectId
from collections import deque

from core.models.semantic_triple import SemanticTriple
from db.connection import get_database


class SemanticTripleRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db[SemanticTriple.Settings.name]

    async def create(self, triple: SemanticTriple) -> SemanticTriple:
        """创建新的语义三元组"""
        result = await triple.insert()
        return result

    async def get_by_id(self, triple_id: str) -> Optional[SemanticTriple]:
        """通过ID获取语义三元组"""
        try:
            return await SemanticTriple.get(ObjectId(triple_id))
        except:
            return None

    async def find_one(self, query: Dict[str, Any]) -> Optional[SemanticTriple]:
        """查找单个语义三元组"""
        return await SemanticTriple.find_one(query)

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[SemanticTriple]:
        """查找多个语义三元组"""
        find_query = SemanticTriple.find(query)

        if sort:
            find_query = find_query.sort(sort)
        else:
            find_query = find_query.sort([("created_at", -1)])

        return await find_query.skip(skip).limit(limit).to_list()

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await SemanticTriple.find(query).count()

    async def update(self, triple_id: str, data: Dict[str, Any]):
        """更新语义三元组"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(triple_id)},
                {"$set": {**data, "updated_at": datetime.now()}}
            )
            return result
        except Exception as e:
            raise Exception(f"更新语义三元组失败: {str(e)}")

    async def delete(self, triple_id: str):
        """删除语义三元组"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(triple_id)})
            return result
        except Exception as e:
            raise Exception(f"删除语义三元组失败: {str(e)}")

    async def get_unit_relations(self, unit_id: str, relation_type: Optional[str] = None,
                                 direction: str = "both", limit: int = 100,
                                 skip: int = 0) -> List[SemanticTriple]:
        """获取与知识单元相关的所有关系"""
        query = {}

        if direction == "outgoing" or direction == "both":
            query["$or"] = [{"subject_id": ObjectId(unit_id)}]

        if direction == "incoming" or direction == "both":
            if "$or" in query:
                query["$or"].append({"object_id": ObjectId(unit_id)})
            else:
                query["$or"] = [{"object_id": ObjectId(unit_id)}]

        if relation_type:
            query["relation_type"] = relation_type

        return await self.find(query, limit, skip)

    async def count_unit_relations(self, unit_id: str, relation_type: Optional[str] = None,
                                   direction: str = "both") -> int:
        """计数与知识单元相关的关系"""
        query = {}

        if direction == "outgoing" or direction == "both":
            query["$or"] = [{"subject_id": ObjectId(unit_id)}]

        if direction == "incoming" or direction == "both":
            if "$or" in query:
                query["$or"].append({"object_id": ObjectId(unit_id)})
            else:
                query["$or"] = [{"object_id": ObjectId(unit_id)}]

        if relation_type:
            query["relation_type"] = relation_type

        return await self.count(query)

    async def find_path(self, start_id: str, end_id: str, max_depth: int = 3):
        """寻找两个知识单元之间的关系路径"""
        # 广度优先搜索
        visited = set()
        queue = deque([(start_id, [])])

        try:
            start_oid = ObjectId(start_id)
            end_oid = ObjectId(end_id)

            while queue and max_depth > 0:
                level_size = len(queue)

                for _ in range(level_size):
                    current_id, path = queue.popleft()
                    current_oid = ObjectId(current_id)

                    if current_id in visited:
                        continue

                    visited.add(current_id)

                    # 检查是否到达目标
                    if current_id == end_id:
                        return path

                    # 获取相关三元组
                    outgoing = await self.find({"subject_id": current_oid}, limit=100)
                    for triple in outgoing:
                        next_id = str(triple.object_id)
                        if next_id not in visited:
                            new_path = path + [{"triple_id": str(triple.id), "direction": "outgoing"}]
                            queue.append((next_id, new_path))

                    incoming = await self.find({"object_id": current_oid}, limit=100)
                    for triple in incoming:
                        next_id = str(triple.subject_id)
                        if next_id not in visited:
                            new_path = path + [{"triple_id": str(triple.id), "direction": "incoming"}]
                            queue.append((next_id, new_path))

                max_depth -= 1

            return None  # 未找到路径
        except Exception as e:
            raise Exception(f"寻找路径失败: {str(e)}")

    async def bulk_insert(self, triples: List[SemanticTriple]) -> List[SemanticTriple]:
        """批量插入语义三元组"""
        if not triples:
            return []

        result = await SemanticTriple.insert_many(triples)
        return result