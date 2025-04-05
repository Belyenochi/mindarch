# core/services/knowledge_graph.py
from typing import Dict, List, Optional, Any, Set
from datetime import datetime
from bson import ObjectId

from db.repositories.knowledge_graph_repo import KnowledgeGraphRepository
from core.models.knowledge_graph import KnowledgeGraph


class KnowledgeGraphService:
    """知识图谱服务"""

    def __init__(self):
        self.repository = KnowledgeGraphRepository()

    async def create(self, graph_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的知识图谱"""
        # 验证数据
        if not self._validate_graph_data(graph_data):
            return {"status": "error", "message": "无效的图谱数据"}

        # 检查名称是否重复
        owner_id = graph_data.get("owner_id")
        name = graph_data.get("name")

        existing = await self.repository.find_one({
            "name": name,
            "owner_id": owner_id
        })

        if existing:
            return {"status": "error", "message": "同名图谱已存在"}

        # 准备创建数据
        if "created_at" not in graph_data:
            graph_data["created_at"] = datetime.now()
        if "updated_at" not in graph_data:
            graph_data["updated_at"] = datetime.now()

        # 转换ID列表字段
        id_list_fields = ["root_units", "included_units", "included_triples"]
        for field in id_list_fields:
            if field in graph_data and graph_data[field]:
                graph_data[field] = [
                    ObjectId(id) if isinstance(id, str) else id
                    for id in graph_data[field]
                ]

        # 计算实体和关系数量
        if "entity_count" not in graph_data:
            graph_data["entity_count"] = len(graph_data.get("included_units", []))
        if "relation_count" not in graph_data:
            graph_data["relation_count"] = len(graph_data.get("included_triples", []))

        # 创建图谱
        graph = KnowledgeGraph(**graph_data)
        result = await self.repository.create(graph)

        return {"status": "success", "graph_id": str(result.id)}

    async def get(self, graph_id: str) -> Optional[KnowledgeGraph]:
        """获取单个知识图谱"""
        return await self.repository.get_by_id(graph_id)

    async def update(self, graph_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识图谱"""
        # 验证图谱存在
        existing = await self.repository.get_by_id(graph_id)
        if not existing:
            return {"status": "error", "message": "知识图谱不存在"}

        # 准备更新数据
        update_data["updated_at"] = datetime.now()

        # 转换ID列表字段
        id_list_fields = ["root_units", "included_units", "included_triples"]
        for field in id_list_fields:
            if field in update_data and update_data[field]:
                update_data[field] = [
                    ObjectId(id) if isinstance(id, str) else id
                    for id in update_data[field]
                ]

        # 执行更新
        result = await self.repository.update(graph_id, update_data)

        return {
            "status": "success",
            "matched": result.matched_count,
            "modified": result.modified_count
        }

    async def delete(self, graph_id: str) -> Dict[str, Any]:
        """删除知识图谱"""
        # 验证图谱存在
        existing = await self.repository.get_by_id(graph_id)
        if not existing:
            return {"status": "error", "message": "知识图谱不存在"}

        # 执行删除
        result = await self.repository.delete(graph_id)

        return {
            "status": "success",
            "deleted": result.deleted_count
        }

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[KnowledgeGraph]:
        """查找知识图谱"""
        return await self.repository.find(query, limit, skip, sort)

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await self.repository.count(query)

    async def add_units(self, graph_id: str, unit_ids: List[str]) -> Dict[str, Any]:
        """向知识图谱添加知识单元"""
        return await self.repository.add_units(graph_id, unit_ids)

    async def add_triples(self, graph_id: str, triple_ids: List[str]) -> Dict[str, Any]:
        """向知识图谱添加语义三元组"""
        return await self.repository.add_triples(graph_id, triple_ids)

    async def get_visual_data(self, graph_id: str, depth: int = 2,
                              root_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """获取图谱可视化数据"""
        return await self.repository.get_graph_visual_data(graph_id, depth, root_ids)

    async def get_stats(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return await self.repository.get_graph_stats(graph_id)

    # 内部辅助方法

    def _validate_graph_data(self, data: Dict[str, Any]) -> bool:
        """验证知识图谱数据"""
        # 必需字段
        if not all(key in data for key in ["name", "owner_id"]):
            return False

        # 名称不能为空
        if not data.get("name", "").strip():
            return False

        return True