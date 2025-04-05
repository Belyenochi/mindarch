# core/services/semantic_triple.py
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId

from db.repositories.semantic_triple_repo import SemanticTripleRepository
from db.repositories.knowledge_unit_repo import KnowledgeUnitRepository
from core.models.semantic_triple import SemanticTriple


class SemanticTripleService:
    """语义三元组服务"""

    def __init__(self):
        self.repository = SemanticTripleRepository()
        self.unit_repository = KnowledgeUnitRepository()

    async def create(self, triple_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的语义三元组"""
        # 验证数据
        if not self._validate_triple_data(triple_data):
            return {"status": "error", "message": "无效的三元组数据"}

        # 检查主语和宾语是否存在
        subject_id = triple_data.get("subject_id")
        object_id = triple_data.get("object_id")

        subject = await self.unit_repository.get_by_id(subject_id)
        object = await self.unit_repository.get_by_id(object_id)

        if not subject or not object:
            return {"status": "error", "message": "主语或宾语单元不存在"}

        # 检查是否已存在相同三元组
        existing = await self._find_duplicate(triple_data)
        # core/services/semantic_triple.py (continued)
        if existing:
            return {"status": "duplicate", "triple_id": str(existing.id)}

        # 准备创建数据
        if isinstance(triple_data.get("subject_id"), str):
            triple_data["subject_id"] = ObjectId(triple_data["subject_id"])

        if isinstance(triple_data.get("object_id"), str):
            triple_data["object_id"] = ObjectId(triple_data["object_id"])

        if triple_data.get("source_id") and isinstance(triple_data["source_id"], str):
            triple_data["source_id"] = ObjectId(triple_data["source_id"])

        if "created_at" not in triple_data:
            triple_data["created_at"] = datetime.now()
        if "updated_at" not in triple_data:
            triple_data["updated_at"] = datetime.now()

        # 创建三元组
        triple = SemanticTriple(**triple_data)
        result = await self.repository.create(triple)

        # 更新知识单元的关系计数
        await self.unit_repository.update(
            str(triple.subject_id),
            {"$inc": {"metrics.outgoing_relations": 1}}
        )

        await self.unit_repository.update(
            str(triple.object_id),
            {"$inc": {"metrics.incoming_relations": 1}}
        )

        return {"status": "success", "triple_id": str(result.id)}

    async def get(self, triple_id: str) -> Optional[SemanticTriple]:
        """获取单个语义三元组"""
        return await self.repository.get_by_id(triple_id)

    async def update(self, triple_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新语义三元组"""
        # 验证三元组存在
        existing = await self.repository.get_by_id(triple_id)
        if not existing:
            return {"status": "error", "message": "语义三元组不存在"}

        # 准备更新数据
        update_data["updated_at"] = datetime.now()

        # 执行更新
        result = await self.repository.update(triple_id, update_data)

        return {
            "status": "success",
            "matched": result.matched_count,
            "modified": result.modified_count
        }

    async def delete(self, triple_id: str) -> Dict[str, Any]:
        """删除语义三元组"""
        # 验证三元组存在
        existing = await self.repository.get_by_id(triple_id)
        if not existing:
            return {"status": "error", "message": "语义三元组不存在"}

        # 更新知识单元的关系计数
        await self.unit_repository.update(
            str(existing.subject_id),
            {"$inc": {"metrics.outgoing_relations": -1}}
        )

        await self.unit_repository.update(
            str(existing.object_id),
            {"$inc": {"metrics.incoming_relations": -1}}
        )

        # 执行删除
        result = await self.repository.delete(triple_id)

        return {
            "status": "success",
            "deleted": result.deleted_count
        }

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[SemanticTriple]:
        """查找语义三元组"""
        return await self.repository.find(query, limit, skip, sort)

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await self.repository.count(query)

    async def get_unit_relations(self, unit_id: str, relation_type: Optional[str] = None,
                                 direction: str = "both", limit: int = 100,
                                 skip: int = 0) -> List[SemanticTriple]:
        """获取与知识单元相关的所有关系"""
        return await self.repository.get_unit_relations(
            unit_id, relation_type, direction, limit, skip
        )

    async def count_unit_relations(self, unit_id: str, relation_type: Optional[str] = None,
                                   direction: str = "both") -> int:
        """计数与知识单元相关的关系"""
        return await self.repository.count_unit_relations(unit_id, relation_type, direction)

    async def find_path(self, start_id: str, end_id: str, max_depth: int = 3):
        """寻找两个知识单元之间的关系路径"""
        return await self.repository.find_path(start_id, end_id, max_depth)

    async def bulk_create(self, triples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量创建语义三元组"""
        triple_objects = []
        skipped = 0

        for triple_data in triples:
            # 验证数据
            if not self._validate_triple_data(triple_data):
                skipped += 1
                continue

            # 准备创建数据
            if isinstance(triple_data.get("subject_id"), str):
                triple_data["subject_id"] = ObjectId(triple_data["subject_id"])

            if isinstance(triple_data.get("object_id"), str):
                triple_data["object_id"] = ObjectId(triple_data["object_id"])

            if triple_data.get("source_id") and isinstance(triple_data["source_id"], str):
                triple_data["source_id"] = ObjectId(triple_data["source_id"])

            if "created_at" not in triple_data:
                triple_data["created_at"] = datetime.now()
            if "updated_at" not in triple_data:
                triple_data["updated_at"] = datetime.now()

            triple = SemanticTriple(**triple_data)
            triple_objects.append(triple)

        if not triple_objects:
            return {"status": "error", "message": "没有有效的三元组数据"}

        # 批量创建
        result = await self.repository.bulk_insert(triple_objects)

        # 更新知识单元的关系计数（批量版本）
        subject_counts = {}
        object_counts = {}

        for triple in result:
            subject_id = str(triple.subject_id)
            object_id = str(triple.object_id)

            subject_counts[subject_id] = subject_counts.get(subject_id, 0) + 1
            object_counts[object_id] = object_counts.get(object_id, 0) + 1

        for subject_id, count in subject_counts.items():
            await self.unit_repository.update(
                subject_id,
                {"$inc": {"metrics.outgoing_relations": count}}
            )

        for object_id, count in object_counts.items():
            await self.unit_repository.update(
                object_id,
                {"$inc": {"metrics.incoming_relations": count}}
            )

        return {
            "status": "success",
            "created": len(result),
            "skipped": skipped,
            "triple_ids": [str(triple.id) for triple in result]
        }

        # 内部辅助方法

    def _validate_triple_data(self, data: Dict[str, Any]) -> bool:
        """验证语义三元组数据"""
        # 必需字段
        if not all(key in data for key in ["subject_id", "predicate", "object_id"]):
            return False

        # 主语和宾语不能相同
        if data["subject_id"] == data["object_id"]:
            return False

        # 谓词不能为空
        if not data.get("predicate", "").strip():
            return False

        return True

    async def _find_duplicate(self, data: Dict[str, Any]) -> Optional[SemanticTriple]:
        """查找是否存在重复的语义三元组"""
        subject_id = data["subject_id"]
        predicate = data["predicate"]
        object_id = data["object_id"]

        if isinstance(subject_id, str):
            subject_id = ObjectId(subject_id)

        if isinstance(object_id, str):
            object_id = ObjectId(object_id)

        return await self.repository.find_one({
            "subject_id": subject_id,
            "predicate": predicate,
            "object_id": object_id
        })