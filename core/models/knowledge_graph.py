from datetime import datetime
from typing import Dict, List, Optional, Any, Literal

from beanie import Document, Indexed, PydanticObjectId  # 导入 PydanticObjectId
from pydantic import Field, ConfigDict, validator


class KnowledgeGraph(Document):
    """知识图谱模型"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={PydanticObjectId: str}  # 序列化时将 PydanticObjectId 转换为字符串
    )

    name: str  # 图谱名称
    description: str = ""  # 图谱描述
    owner_id: Indexed(str)  # 所有者ID
    is_public: Indexed(str) = "false"  # 是否公开，使用字符串类型并建立索引
    root_units: List[PydanticObjectId] = Field(default_factory=list)  # 根知识单元ID
    included_units: List[PydanticObjectId] = Field(default_factory=list)  # 包含的知识单元ID
    included_triples: List[PydanticObjectId] = Field(default_factory=list)  # 包含的三元组ID
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: Indexed(str) = "active"  # active, archived
    version: str = "1.0"
    entity_count: int = 0
    relation_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据
    visual_settings: Dict[str, Any] = Field(default_factory=dict)  # 可视化设置

    # 验证 is_public 的值只能是 "true" 或 "false"
    @validator("is_public")
    def validate_is_public(cls, v):
        if v not in ["true", "false"]:
            raise ValueError("is_public must be 'true' or 'false'")
        return v

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
            data["_id"] = PydanticObjectId(data.pop("id"))

        # 转换ID列表
        if "root_units" in data:
            data["root_units"] = [PydanticObjectId(id) if isinstance(id, str) else id
                                  for id in data["root_units"]]

        if "included_units" in data:
            data["included_units"] = [PydanticObjectId(id) if isinstance(id, str) else id
                                      for id in data["included_units"]]

        if "included_triples" in data:
            data["included_triples"] = [PydanticObjectId(id) if isinstance(id, str) else id
                                        for id in data["included_triples"]]

        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)