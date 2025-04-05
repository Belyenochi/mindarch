# core/models/knowledge_graph.py
from datetime import datetime
from typing import Dict, List, Optional, Any

from beanie import Document, Indexed
from pydantic import Field
from bson import ObjectId


class KnowledgeGraph(Document):
    """知识图谱模型"""
    name: str  # 图谱名称
    description: str = ""  # 图谱描述
    owner_id: Indexed(str)  # 所有者ID
    is_public: Indexed(bool) = False  # 是否公开
    root_units: List[ObjectId] = Field(default_factory=list)  # 根知识单元ID
    included_units: List[ObjectId] = Field(default_factory=list)  # 包含的知识单元ID
    included_triples: List[ObjectId] = Field(default_factory=list)  # 包含的三元组ID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: Indexed(str) = "active"  # active, archived
    version: str = "1.0"
    entity_count: int = 0
    relation_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据
    visual_settings: Dict[str, Any] = Field(default_factory=dict)  # 可视化设置

    class Settings:
        name = "knowledge_graphs"
        indexes = [
            [("name", 1), ("owner_id", 1)],
            "owner_id",
            "is_public",
            "status",
            "created_at",
            {"keys": [("name", "text"), ("description", "text")],
             "default_language": "zh",
             "weights": {"name": 10, "description": 5}}
        ]

    def to_json(self):
        """转换为JSON表示"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "is_public": self.is_public,
            "root_units": [str(id) for id in self.root_units],
            "included_units": [str(id) for id in self.included_units],
            "included_triples": [str(id) for id in self.included_triples],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "status": self.status,
            "version": self.version,
            "entity_count": self.entity_count,
            "relation_count": self.relation_count,
            "metadata": self.metadata,
            "visual_settings": self.visual_settings
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "KnowledgeGraph":
        """从JSON创建实例"""
        if "id" in data:
            data["_id"] = ObjectId(data.pop("id"))

        # 转换ID列表
        if "root_units" in data:
            data["root_units"] = [ObjectId(id) if isinstance(id, str) else id
                                  for id in data["root_units"]]

        if "included_units" in data:
            data["included_units"] = [ObjectId(id) if isinstance(id, str) else id
                                      for id in data["included_units"]]

        if "included_triples" in data:
            data["included_triples"] = [ObjectId(id) if isinstance(id, str) else id
                                        for id in data["included_triples"]]

        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)