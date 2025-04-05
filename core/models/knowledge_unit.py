# core/models/knowledge_unit.py
from datetime import datetime
from typing import Dict, List, Optional, Any

from beanie import Document, Link, Indexed
from pydantic import BaseModel, Field
from bson import ObjectId


class Source(BaseModel):
    """知识来源信息"""
    file_id: Optional[str] = None
    file_name: Optional[str] = ""
    import_id: Optional[str] = None
    position: int = 0
    section: str = ""


class Status(BaseModel):
    """知识状态信息"""
    state: str = "draft"  # draft, active, merged, archived
    is_duplicate: bool = False
    is_empty: bool = False
    validation: str = "pending"  # pending, validated, rejected


class Knowledge(BaseModel):
    """知识表示"""
    domain: str = ""
    entity_type: str = "concept"
    importance: int = 3
    abstraction_level: int = 3
    properties: Dict[str, Any] = Field(default_factory=dict)


class Metrics(BaseModel):
    """度量指标"""
    confidence: float = 0.7
    completeness: float = 0.5
    outgoing_relations: int = 0
    incoming_relations: int = 0
    citation_count: int = 0
    view_count: int = 0


class KnowledgeUnit(Document):
    """知识单元模型"""
    title: str
    content: str
    unit_type: Indexed(str) = "note"  # note, entity, concept, etc.
    canonical_name: Indexed(str)
    aliases: List[str] = Field(default_factory=list)
    tags: List[Indexed(str)] = Field(default_factory=list)
    source: Source = Field(default_factory=Source)
    status: Status = Field(default_factory=Status)
    knowledge: Knowledge = Field(default_factory=Knowledge)
    metrics: Metrics = Field(default_factory=Metrics)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: str = "system"
    merged_units: List[str] = Field(default_factory=list)
    parent_units: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "knowledge_units"
        indexes = [
            "canonical_name",
            "unit_type",
            "tags",
            "source.file_id",
            "source.import_id",
            "status.state",
            "created_at",
            [("canonical_name", 1), ("unit_type", 1)],
            [("unit_type", 1), ("knowledge.domain", 1)],
            {"keys": [("title", "text"), ("content", "text"),
                      ("canonical_name", "text"), ("aliases", "text")],
             "default_language": "zh",
             "weights": {"title": 10, "content": 5, "canonical_name": 8, "aliases": 6}}
        ]

    def to_json(self):
        """转换为JSON表示"""
        return {
            "id": str(self.id),
            "title": self.title,
            "content": self.content,
            "unit_type": self.unit_type,
            "canonical_name": self.canonical_name,
            "aliases": self.aliases,
            "tags": self.tags,
            "source": self.source.dict(),
            "status": self.status.dict(),
            "knowledge": self.knowledge.dict(),
            "metrics": self.metrics.dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "merged_units": self.merged_units,
            "parent_units": self.parent_units,
            "metadata": self.metadata
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "KnowledgeUnit":
        """从JSON创建实例"""
        if "id" in data:
            data["_id"] = ObjectId(data.pop("id"))

        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)