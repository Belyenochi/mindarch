# api/routes/semantic_triples.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer

from api.schemas.semantic_triples import (
    SemanticTripleCreate,
    SemanticTripleResponse,
    SemanticTripleUpdate,
    SemanticTripleList,
    PathRequest,
    PathResponse
)
from core.services.semantic_triple import SemanticTripleService
from services.auth import get_current_user

router = APIRouter(prefix="/triples", tags=["语义三元组"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# 依赖注入
def get_triple_service():
    return SemanticTripleService()


@router.post("/", response_model=SemanticTripleResponse, status_code=201)
async def create_triple(
        triple: SemanticTripleCreate,
        service: SemanticTripleService = Depends(get_triple_service),
        token: str = Depends(oauth2_scheme)
):
    """创建新的语义三元组"""
    user = await get_current_user(token)

    result = await service.create(triple.dict())

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    elif result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail=f"发现重复三元组: {result['triple_id']}")

    return {"status": "success", "triple_id": result["triple_id"]}


@router.get("/{triple_id}", response_model=SemanticTripleResponse)
async def get_triple(
        triple_id: str = Path(..., description="三元组ID"),
        service: SemanticTripleService = Depends(get_triple_service)
):
    """获取单个语义三元组"""
    triple = await service.get(triple_id)
    if not triple:
        raise HTTPException(status_code=404, detail="三元组不存在")
    return triple


@router.put("/{triple_id}", response_model=SemanticTripleResponse)
async def update_triple(
        update_data: SemanticTripleUpdate,
        triple_id: str = Path(..., description="三元组ID"),
        service: SemanticTripleService = Depends(get_triple_service),
        token: str = Depends(oauth2_scheme)
):
    """更新语义三元组"""
    user = await get_current_user(token)

    result = await service.update(triple_id, update_data.dict(exclude_unset=True))

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    updated_triple = await service.get(triple_id)
    return updated_triple


@router.delete("/{triple_id}", status_code=204)
async def delete_triple(
        triple_id: str = Path(..., description="三元组ID"),
        service: SemanticTripleService = Depends(get_triple_service),
        token: str = Depends(oauth2_scheme)
):
    """删除语义三元组"""
    user = await get_current_user(token)

    result = await service.delete(triple_id)

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return None


@router.get("/", response_model=SemanticTripleList)
async def list_triples(
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        relation_type: Optional[str] = Query(None),
        service: SemanticTripleService = Depends(get_triple_service)
):
    """获取语义三元组列表"""
    query = {}
    if relation_type:
        query["relation_type"] = relation_type

    triples = await service.find(query, limit, skip)
    total = await service.count(query)

    return {
        "items": triples,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/by-unit/{unit_id}", response_model=SemanticTripleList)
async def get_unit_relations(
        unit_id: str = Path(..., description="知识单元ID"),
        direction: str = Query("both", description="关系方向: outgoing, incoming, both"),
        relation_type: Optional[str] = Query(None, description="关系类型"),
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        service: SemanticTripleService = Depends(get_triple_service)
):
    """获取与知识单元相关的所有关系"""
    if direction not in ["outgoing", "incoming", "both"]:
        raise HTTPException(status_code=400, detail="无效的关系方向")

    triples = await service.get_unit_relations(unit_id, relation_type, direction, limit, skip)
    total = await service.count_unit_relations(unit_id, relation_type, direction)

    return {
        "items": triples,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.post("/path", response_model=PathResponse)
async def find_path(
        path_request: PathRequest,
        service: SemanticTripleService = Depends(get_triple_service)
):
    """寻找两个知识单元之间的关系路径"""
    path = await service.find_path(
        path_request.start_id,
        path_request.end_id,
        path_request.max_depth
    )

    if not path:
        return {"status": "not_found", "path": []}

    return {"status": "success", "path": path}