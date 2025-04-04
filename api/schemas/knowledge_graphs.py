# api/schemas/knowledge_graphs.py
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# 请求模型
class KnowledgeGraphCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    is_public: bool = False
    root_units: Optional[List[str]] = None
    included_units: Optional[List[str]] = None
    included_triples: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    visual_settings: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "计算机科学基础概念",
                "description": "计算机科学领域的核心概念和它们之间的关系",
                "is_public": True,
                "root_units": ["6123456789abcdef01234567"],
                "metadata": {
                    "domain": "计算机科学",
                    "tags": ["教育", "入门"]
                },
                "visual_settings": {
                    "layout": "force",
                    "theme": "light"
                }
            }
        }


class KnowledgeGraphUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None
    root_units: Optional[List[str]] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    visual_settings: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "name": "计算机科学核心概念",
                "description": "更新后的描述",
                "visual_settings": {
                    "layout": "hierarchical",
                    "theme": "dark"
                }
            }
        }


# 响应模型
class KnowledgeGraphResponse(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    owner_id: str
    entity_count: int
    relation_count: int
    root_units: List[str]
    status: str
    version: str
    is_public: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)
    visual_settings: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphList(BaseModel):
    items: List[KnowledgeGraphResponse]
    total: int
    limit: int
    skip: int


# 可视化数据
class VisualNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class VisualEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphVisual(BaseModel):
    status: str
    nodes: List[VisualNode]
    edges: List[VisualEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


# 统计信息
class DomainStats(BaseModel):
    domain: str
    count: int


class TypeStats(BaseModel):
    type: str
    count: int


class KnowledgeGraphStats(BaseModel):
    status: str
    total_units: int
    total_triples: int
    unit_types: List[TypeStats]
    relation_types: List[TypeStats]
    domains: List[DomainStats]
    created_at: datetime
    updated_at: datetime