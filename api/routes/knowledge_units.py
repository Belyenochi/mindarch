# api/routes/knowledge_units.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.security import OAuth2PasswordBearer

from api.schemas.knowledge_units import (
    KnowledgeUnitCreate,
    KnowledgeUnitResponse,
    KnowledgeUnitUpdate,
    KnowledgeUnitSearch,
    KnowledgeUnitList
)
from core.services.knowledge_unit import KnowledgeUnitService
from services.auth import get_current_user

router = APIRouter(prefix="/units", tags=["知识单元"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# 依赖注入
def get_unit_service():
    return KnowledgeUnitService()


@router.post("/", response_model=KnowledgeUnitResponse, status_code=201)
async def create_unit(
        unit: KnowledgeUnitCreate,
        service: KnowledgeUnitService = Depends(get_unit_service),
        token: str = Depends(oauth2_scheme)
):
    """创建新知识单元"""
    user = await get_current_user(token)

    unit_data = unit.dict()
    unit_data["created_by"] = f"user:{user.id}"

    result = await service.create(unit_data)

    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail=f"发现重复单元: {result['duplicate_id']}")

    return {"status": "success", "unit_id": result["unit_id"]}


@router.get("/{unit_id}", response_model=KnowledgeUnitResponse)
async def get_unit(
        unit_id: str = Path(..., description="知识单元ID"),
        service: KnowledgeUnitService = Depends(get_unit_service)
):
    """获取单个知识单元"""
    unit = await service.get(unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail="知识单元不存在")
    return unit


@router.put("/{unit_id}", response_model=KnowledgeUnitResponse)
async def update_unit(
        update_data: KnowledgeUnitUpdate,
        unit_id: str = Path(..., description="知识单元ID"),
        service: KnowledgeUnitService = Depends(get_unit_service),
        token: str = Depends(oauth2_scheme)
):
    """更新知识单元"""
    user = await get_current_user(token)

    result = await service.update(unit_id, update_data.dict(exclude_unset=True))

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    updated_unit = await service.get(unit_id)
    return updated_unit


@router.delete("/{unit_id}", status_code=204)
async def delete_unit(
        unit_id: str = Path(..., description="知识单元ID"),
        service: KnowledgeUnitService = Depends(get_unit_service),
        token: str = Depends(oauth2_scheme)
):
    """删除知识单元"""
    user = await get_current_user(token)

    result = await service.delete(unit_id)

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result["message"])

    return None


@router.get("/", response_model=KnowledgeUnitList)
async def list_units(
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        unit_type: Optional[str] = Query(None),
        domain: Optional[str] = Query(None),
        sort_by: Optional[str] = Query("created_at"),
        sort_order: Optional[str] = Query("desc"),
        service: KnowledgeUnitService = Depends(get_unit_service)
):
    """获取知识单元列表"""
    # 构建查询
    query = {}
    if unit_type:
        query["unit_type"] = unit_type
    if domain:
        query["knowledge.domain"] = domain

    # 构建排序
    sort = []
    if sort_by:
        sort_direction = -1 if sort_order.lower() == "desc" else 1
        sort.append((sort_by, sort_direction))

    units = await service.find(query, limit, skip, sort)
    total = await service.count(query)

    return {
        "items": units,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.post("/search", response_model=KnowledgeUnitList)
async def search_units(
        search: KnowledgeUnitSearch,
        service: KnowledgeUnitService = Depends(get_unit_service)
):
    """搜索知识单元"""
    units = await service.search(
        search.query,
        search.filters,
        search.limit,
        search.skip
    )

    total = await service.count_search(search.query, search.filters)

    return {
        "items": units,
        "total": total,
        "limit": search.limit,
        "skip": search.skip
    }


@router.post("/merge", response_model=KnowledgeUnitResponse)
async def merge_units(
        primary_id: str = Query(..., description="主要单元ID"),
        secondary_ids: List[str] = Query(..., description="次要单元ID列表"),
        service: KnowledgeUnitService = Depends(get_unit_service),
        token: str = Depends(oauth2_scheme)
):
    """合并多个知识单元"""
    user = await get_current_user(token)

    result = await service.merge(primary_id, secondary_ids)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    merged_unit = await service.get(primary_id)
    return merged_unit