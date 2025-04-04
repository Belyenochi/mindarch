# db/repositories/knowledge_graph_repo.py
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from bson.objectid import ObjectId

from core.models.knowledge_graph import KnowledgeGraph
from core.models.knowledge_unit import KnowledgeUnit
from core.models.semantic_triple import SemanticTriple
from db.connection import get_database


class KnowledgeGraphRepository:
    def __init__(self):
        self.db = get_database()
        self.collection = self.db[KnowledgeGraph.Settings.name]
        self.units_collection = self.db[KnowledgeUnit.Settings.name]
        self.triples_collection = self.db[SemanticTriple.Settings.name]

    async def create(self, graph: KnowledgeGraph) -> KnowledgeGraph:
        """创建新的知识图谱"""
        result = await graph.insert()
        return result

    async def get_by_id(self, graph_id: str) -> Optional[KnowledgeGraph]:
        """通过ID获取知识图谱"""
        try:
            return await KnowledgeGraph.get(ObjectId(graph_id))
        except:
            return None

    async def find_one(self, query: Dict[str, Any]) -> Optional[KnowledgeGraph]:
        """查找单个知识图谱"""
        return await KnowledgeGraph.find_one(query)

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[KnowledgeGraph]:
        """查找多个知识图谱"""
        find_query = KnowledgeGraph.find(query)

        if sort:
            find_query = find_query.sort(sort)
        else:
            find_query = find_query.sort([("created_at", -1)])

        return await find_query.skip(skip).limit(limit).to_list()

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await KnowledgeGraph.find(query).count()

    async def update(self, graph_id: str, data: Dict[str, Any]):
        """更新知识图谱"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(graph_id)},
                {"$set": {**data, "updated_at": datetime.now()}}
            )
            return result
        except Exception as e:
            raise Exception(f"更新知识图谱失败: {str(e)}")

    async def delete(self, graph_id: str):
        """删除知识图谱"""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(graph_id)})
            return result
        except Exception as e:
            raise Exception(f"删除知识图谱失败: {str(e)}")

    async def add_units(self, graph_id: str, unit_ids: List[str]):
        """向知识图谱添加知识单元"""
        try:
            graph = await self.get_by_id(graph_id)
            if not graph:
                return {"status": "error", "message": "知识图谱不存在"}

            # 转换ID为ObjectId
            obj_ids = [ObjectId(id) for id in unit_ids]

            # 查找现有单元
            existing_units = set(str(id) for id in graph.included_units) if graph.included_units else set()

            # 计算新增单元
            new_units = [id for id in unit_ids if id not in existing_units]

            if not new_units:
                return {"status": "success", "added": 0}

            # 更新图谱
            result = await self.collection.update_one(
                {"_id": ObjectId(graph_id)},
                {
                    "$addToSet": {"included_units": {"$each": obj_ids}},
                    "$set": {"updated_at": datetime.now()},
                    "$inc": {"entity_count": len(new_units)}
                }
            )

            return {"status": "success", "added": len(new_units)}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def add_triples(self, graph_id: str, triple_ids: List[str]):
        """向知识图谱添加语义三元组"""
        try:
            graph = await self.get_by_id(graph_id)
            if not graph:
                return {"status": "error", "message": "知识图谱不存在"}

            # 转换ID为ObjectId
            obj_ids = [ObjectId(id) for id in triple_ids]

            # 查找现有三元组
            existing_triples = set(str(id) for id in graph.included_triples) if graph.included_triples else set()

            # 计算新增三元组
            new_triples = [id for id in triple_ids if id not in existing_triples]

            if not new_triples:
                return {"status": "success", "added": 0}

            # 更新图谱
            result = await self.collection.update_one(
                {"_id": ObjectId(graph_id)},
                {
                    "$addToSet": {"included_triples": {"$each": obj_ids}},
                    "$set": {"updated_at": datetime.now()},
                    "$inc": {"relation_count": len(new_triples)}
                }
            )

            # 提取并添加三元组相关的单元
            triples = await self.triples_collection.find({"_id": {"$in": obj_ids}}).to_list(None)

            unit_ids = set()
            for triple in triples:
                unit_ids.add(triple["subject_id"])
                unit_ids.add(triple["object_id"])

            # 自动添加相关单元
            if unit_ids:
                await self.add_units(graph_id, [str(id) for id in unit_ids])

            return {"status": "success", "added": len(new_triples)}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_graph_visual_data(self, graph_id: str, depth: int = 2, root_ids: Optional[List[str]] = None):
        """获取知识图谱可视化数据"""
        try:
            graph = await self.get_by_id(graph_id)
            if not graph:
                return {"status": "error", "message": "知识图谱不存在"}

            # 确定根节点
            if root_ids:
                roots = [ObjectId(id) for id in root_ids]
            elif graph.root_units:
                roots = graph.root_units
            else:
                # 如果没有指定根节点，使用度最高的节点
                pipeline = [
                    {"$match": {"_id": {"$in": graph.included_units}}},
                    {"$project": {
                        "_id": 1,
                        "title": 1,
                        "unit_type": 1,
                        "score": {"$add": ["$metrics.outgoing_relations", "$metrics.incoming_relations"]}
                    }},
                    {"$sort": {"score": -1}},
                    {"$limit": 5}
                ]

                top_units = await self.units_collection.aggregate(pipeline).to_list(None)
                roots = [unit["_id"] for unit in top_units]

            # 如果仍然没有根节点，使用任何包含的单元
            if not roots and graph.included_units:
                roots = graph.included_units[:5]

            if not roots:
                return {"status": "error", "message": "图谱不包含任何单元"}

            # 收集节点和边
            nodes = {}
            edges = {}

            # 广度优先遍历
            queue = [(root, 0) for root in roots]
            visited_units = set()
            visited_triples = set()

            while queue:
                unit_id, current_depth = queue.pop(0)

                if current_depth > depth:
                    continue

                if unit_id in visited_units:
                    continue

                visited_units.add(unit_id)

                # 获取单元
                unit = await self.units_collection.find_one({"_id": unit_id})
                if not unit:
                    continue

                # 添加节点
                if str(unit_id) not in nodes:
                    nodes[str(unit_id)] = {
                        "id": str(unit_id),
                        "label": unit["title"],
                        "type": unit["unit_type"],
                        "properties": {
                            "canonical_name": unit.get("canonical_name", ""),
                            "importance": unit.get("knowledge", {}).get("importance", 3)
                        }
                    }

                if current_depth == depth:
                    continue

                # 获取出向关系
                outgoing = await self.triples_collection.find({
                    "subject_id": unit_id,
                    "_id": {"$in": graph.included_triples}
                }).to_list(None)

                for triple in outgoing:
                    if triple["_id"] in visited_triples:
                        continue

                    visited_triples.add(triple["_id"])

                    # 添加边
                    if str(triple["_id"]) not in edges:
                        edges[str(triple["_id"])] = {
                            "id": str(triple["_id"]),
                            "source": str(triple["subject_id"]),
                            "target": str(triple["object_id"]),
                            "label": triple["predicate"],
                            "type": triple["relation_type"],
                            "properties": {
                                "confidence": triple.get("confidence", 0.5),
                                "bidirectional": triple.get("bidirectional", False)
                            }
                        }

                    # 添加目标节点到队列
                    if triple["object_id"] not in visited_units:
                        queue.append((triple["object_id"], current_depth + 1))

                # 获取入向关系
                incoming = await self.triples_collection.find({
                    "object_id": unit_id,
                    "_id": {"$in": graph.included_triples}
                }).to_list(None)

                for triple in incoming:
                    if triple["_id"] in visited_triples:
                        continue

                    visited_triples.add(triple["_id"])

                    # 添加边
                    if str(triple["_id"]) not in edges:
                        edges[str(triple["_id"])] = {
                            "id": str(triple["_id"]),
                            "source": str(triple["subject_id"]),
                            "target": str(triple["object_id"]),
                            "label": triple["predicate"],
                            "type": triple["relation_type"],
                            "properties": {
                                "confidence": triple.get("confidence", 0.5),
                                "bidirectional": triple.get("bidirectional", False)
                            }
                        }

                    # 添加源节点到队列
                    if triple["subject_id"] not in visited_units:
                        queue.append((triple["subject_id"], current_depth + 1))

            # 返回可视化数据
            return {
                "status": "success",
                "nodes": list(nodes.values()),
                "edges": list(edges.values()),
                "metadata": {
                    "graph_id": str(graph_id),
                    "graph_name": graph.name,
                    "total_units": len(nodes),
                    "total_relations": len(edges),
                    "depth": depth
                }
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_graph_stats(self, graph_id: str):
        """获取知识图谱统计信息"""
        try:
            graph = await self.get_by_id(graph_id)
            if not graph:
                return {"status": "error", "message": "知识图谱不存在"}

            # 获取单元类型统计
            unit_type_pipeline = [
                {"$match": {"_id": {"$in": graph.included_units}}},
                {"$group": {"_id": "$unit_type", "count": {"$sum": 1}}},
                {"$project": {"type": "$_id", "count": 1, "_id": 0}},
                {"$sort": {"count": -1}}
            ]

            unit_types = await self.units_collection.aggregate(unit_type_pipeline).to_list(None)

            # 获取关系类型统计
            relation_type_pipeline = [
                {"$match": {"_id": {"$in": graph.included_triples}}},
                {"$group": {"_id": "$relation_type", "count": {"$sum": 1}}},
                {"$project": {"type": "$_id", "count": 1, "_id": 0}},
                {"$sort": {"count": -1}}
            ]

            relation_types = await self.triples_collection.aggregate(relation_type_pipeline).to_list(None)

            # 获取领域统计
            domain_pipeline = [
                {"$match": {"_id": {"$in": graph.included_units}}},
                {"$group": {"_id": "$knowledge.domain", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": "", "$ne": None}}},
                {"$project": {"domain": "$_id", "count": 1, "_id": 0}},
                {"$sort": {"count": -1}}
            ]

            domains = await self.units_collection.aggregate(domain_pipeline).to_list(None)

            # 返回统计信息
            return {
                "status": "success",
                "total_units": graph.entity_count,
                "total_triples": graph.relation_count,
                "unit_types": unit_types,
                "relation_types": relation_types,
                "domains": domains,
                "created_at": graph.created_at,
                "updated_at": graph.updated_at
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}