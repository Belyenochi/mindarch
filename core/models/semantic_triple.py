from datetime import datetime
from typing import Dict, Optional, Any

from beanie import Document, Indexed, PydanticObjectId  # 直接导入 Beanie 的 PydanticObjectId
from pydantic import Field, ConfigDict


class SemanticTriple(Document):
    """语义三元组模型"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_encoders={PydanticObjectId: str}  # 序列化时将 PydanticObjectId 转换为字符串
    )

    subject_id: Indexed(PydanticObjectId)  # 主语知识单元ID
    predicate: str  # 谓词/关系
    object_id: Indexed(PydanticObjectId)  # 宾语知识单元ID
    relation_type: Indexed(str) = "generic"  # 关系类型(is-a, part-of等)
    confidence: float = 0.8  # 置信度
    bidirectional: bool = False  # 是否为双向关系
    context: Optional[str] = None  # 上下文描述
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    source_id: Optional[PydanticObjectId] = None  # 来源(文件或知识单元)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # 元数据
    properties: Dict[str, Any] = Field(default_factory=dict)  # 关系属性

    class Settings:
        name = "semantic_triples"
        indexes = [
            [("subject_id", 1), ("predicate", 1), ("object_id", 1)],
            "subject_id",
            "object_id",
            "relation_type",
            "source_id",
            "created_at"
        ]

    def to_json(self):
        """转换为JSON表示"""
        return {
            "id": str(self.id),
            "subject_id": str(self.subject_id),
            "predicate": self.predicate,
            "object_id": str(self.object_id),
            "relation_type": self.relation_type,
            "confidence": self.confidence,
            "bidirectional": self.bidirectional,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "source_id": str(self.source_id) if self.source_id else None,
            "metadata": self.metadata,
            "properties": self.properties
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "SemanticTriple":
        """从JSON创建实例"""
        # 转换 ID 相关字段
        for field in ["id", "subject_id", "object_id", "source_id"]:
            if field in data and isinstance(data[field], str) and data[field]:
                data[field] = PydanticObjectId(data[field])

        # 处理日期字段
        for date_field in ["created_at", "updated_at"]:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = datetime.fromisoformat(data[date_field])

        return cls(**data)