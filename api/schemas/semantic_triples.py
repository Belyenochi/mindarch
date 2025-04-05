# api/schemas/semantic_triples.py
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


# 请求模型
class SemanticTripleCreate(BaseModel):
    subject_id: str
    predicate: str
    object_id: str
    relation_type: str = "generic"
    bidirectional: bool = False
    confidence: float = 0.8
    context: Optional[str] = None
    source_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "subject_id": "6123456789abcdef01234567",
                "predicate": "是一种",
                "object_id": "6123456789abcdef01234568",
                "relation_type": "is-a",
                "bidirectional": False,
                "confidence": 0.95,
                "context": "二叉树是树的一种特殊形式"
            }
        }


class SemanticTripleUpdate(BaseModel):
    predicate: Optional[str] = None
    relation_type: Optional[str] = None
    bidirectional: Optional[bool] = None
    confidence: Optional[float] = None
    context: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "predicate": "属于",
                "relation_type": "belongs-to",
                "confidence": 0.98
            }
        }


class PathRequest(BaseModel):
    start_id: str
    end_id: str
    max_depth: int = 3

    class Config:
        json_schema_extra = {
            "example": {
                "start_id": "6123456789abcdef01234567",
                "end_id": "6123456789abcdef01234569",
                "max_depth": 4
            }
        }


# 响应模型
class SemanticTripleResponse(BaseModel):
    id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float
    relation_type: str
    bidirectional: bool
    created_at: datetime
    updated_at: datetime
    source_id: Optional[str] = None
    context: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    properties: Dict[str, Any] = Field(default_factory=dict)


class PathStep(BaseModel):
    triple_id: str
    direction: str  # "outgoing" or "incoming"


class PathResponse(BaseModel):
    status: str  # "success" or "not_found"
    path: List[PathStep]


class SemanticTripleList(BaseModel):
    items: List[SemanticTripleResponse]
    total: int
    limit: int
    skip: int