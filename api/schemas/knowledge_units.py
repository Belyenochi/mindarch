# api/schemas/knowledge_units.py
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime


# 嵌套模型
class Source(BaseModel):
    file_id: Optional[str] = None
    file_name: Optional[str] = ""
    import_id: Optional[str] = None
    position: int = 0
    section: str = ""


class Status(BaseModel):
    state: str = "draft"
    is_duplicate: bool = False
    is_empty: bool = False
    validation: str = "pending"


class Knowledge(BaseModel):
    domain: str = ""
    entity_type: str = "concept"
    importance: int = 3
    abstraction_level: int = 3
    properties: Dict[str, Any] = Field(default_factory=dict)


class Metrics(BaseModel):
    confidence: float = 0.7
    completeness: float = 0.5
    outgoing_relations: int = 0
    incoming_relations: int = 0
    citation_count: int = 0
    view_count: int = 0


# 请求模型
class KnowledgeUnitCreate(BaseModel):
    title: str
    content: str
    unit_type: str = "note"
    canonical_name: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    source: Optional[Source] = None
    knowledge: Optional[Knowledge] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "二叉树",
                "content": "二叉树是每个节点最多有两个子树的树结构",
                "unit_type": "concept",
                "canonical_name": "binary_tree",
                "aliases": ["binary tree", "二叉树结构"],
                "tags": ["数据结构", "树", "计算机科学"],
                "knowledge": {
                    "domain": "计算机科学",
                    "entity_type": "concept",
                    "importance": 4
                }
            }
        }


class KnowledgeUnitUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    unit_type: Optional[str] = None
    canonical_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None
    knowledge: Optional[Knowledge] = None

    class Config:
        json_schema_extra = {
            "example": {
                "title": "二叉树数据结构",
                "content": "二叉树是每个节点最多有两个子树的树结构，常用于实现二叉搜索树和堆",
                "tags": ["数据结构", "树", "计算机科学", "算法"]
            }
        }


class KnowledgeUnitSearch(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20
    skip: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "query": "二叉树",
                "filters": {"unit_type": "concept", "knowledge.domain": "计算机科学"},
                "limit": 20,
                "skip": 0
            }
        }


# 响应模型
class KnowledgeUnitResponse(BaseModel):
    id: str
    title: str
    content: str
    unit_type: str
    canonical_name: str
    aliases: List[str]
    tags: List[str]
    source: Source
    status: Status
    knowledge: Knowledge
    metrics: Metrics
    created_at: datetime
    updated_at: datetime
    created_by: str
    merged_units: List[str] = Field(default_factory=list)
    parent_units: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeUnitList(BaseModel):
    items: List[KnowledgeUnitResponse]
    total: int
    limit: int
    skip: int