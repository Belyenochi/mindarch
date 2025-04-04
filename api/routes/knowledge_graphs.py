# api/routes/knowledge_graphs.py
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from fastapi.security import OAuth2PasswordBearer

from api.schemas.knowledge_graphs import (
    KnowledgeGraphCreate,
    KnowledgeGraphResponse,
    KnowledgeGraphUpdate,
    KnowledgeGraphList,
    KnowledgeGraphVisual,
    KnowledgeGraphStats
)
from core.services.knowledge_graph import KnowledgeGraphService
from services.auth import get_current_user

router = APIRouter(prefix="/graphs", tags=["知识图谱"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# 依赖注入
def get_graph_service():
    return KnowledgeGraphService()


@router.post("/", response_model=KnowledgeGraphResponse, status_code=201)
async def create_graph(
        graph: KnowledgeGraphCreate,
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: str = Depends(oauth2_scheme)
):
    """创建新知识图谱"""
    user = await get_current_user(token)

    graph_data = graph.dict()
    graph_data["owner_id"] = user.id

    result = await service.create(graph_data)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return {"status": "success", "graph_id": result["graph_id"]}


@router.get("/{graph_id}", response_model=KnowledgeGraphResponse)
async def get_graph(
        graph_id: str = Path(..., description="知识图谱ID"),
        service: KnowledgeGraphService = Depends(get_graph_service)
):
    """获取单个知识图谱"""
    graph = await service.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")
    return graph


@router.put("/{graph_id}", response_model=KnowledgeGraphResponse)
async def update_graph(
        update_data: KnowledgeGraphUpdate,
        graph_id: str = Path(..., description="知识图谱ID"),
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: str = Depends(oauth2_scheme)
):
    """更新知识图谱"""
    user = await get_current_user(token)

    # 检查所有权
    graph = await service.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")

    if graph.owner_id != user.id:
        raise HTTPException(status_code=403, detail="没有权限修改此知识图谱")

    result = await service.update(graph_id, update_data.dict(exclude_unset=True))

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    updated_graph = await service.get(graph_id)
    return updated_graph


@router.delete("/{graph_id}", status_code=204)
async def delete_graph(
        graph_id: str = Path(..., description="知识图谱ID"),
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: str = Depends(oauth2_scheme)
):
    """删除知识图谱"""
    user = await get_current_user(token)

    # 检查所有权
    graph = await service.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")

    if graph.owner_id != user.id:
        raise HTTPException(status_code=403, detail="没有权限删除此知识图谱")

    result = await service.delete(graph_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return None


@router.get("/", response_model=KnowledgeGraphList)
async def list_graphs(
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        is_public: Optional[bool] = Query(None),
        owner_id: Optional[str] = Query(None),
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: Optional[str] = Depends(oauth2_scheme)
):
    """获取知识图谱列表"""
    user = None
    if token:
        user = await get_current_user(token)

    query = {}
    if is_public is not None:
        query["is_public"] = is_public
    if owner_id:
        query["owner_id"] = owner_id
    elif user:
        # 如果是已登录用户，显示他们的图谱和公开图谱
        query["$or"] = [{"owner_id": user.id}, {"is_public": True}]
    else:
        # 如果是匿名用户，只显示公开图谱
        query["is_public"] = True

    graphs = await service.find(query, limit, skip)
    total = await service.count(query)

    return {
        "items": graphs,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/{graph_id}/visual", response_model=KnowledgeGraphVisual)
async def get_graph_visual(
        graph_id: str = Path(..., description="知识图谱ID"),
        depth: int = Query(2, ge=1, le=5, description="展开深度"),
        root_ids: Optional[List[str]] = Query(None, description="根节点ID列表"),
        service: KnowledgeGraphService = Depends(get_graph_service)
):
    """获取知识图谱可视化数据"""
    visual_data = await service.get_visual_data(graph_id, depth, root_ids)

    if visual_data["status"] == "error":
        raise HTTPException(status_code=404, detail=visual_data["message"])

    return visual_data


@router.get("/{graph_id}/stats", response_model=KnowledgeGraphStats)
async def get_graph_stats(
        graph_id: str = Path(..., description="知识图谱ID"),
        service: KnowledgeGraphService = Depends(get_graph_service)
):
    """获取知识图谱统计信息"""
    stats = await service.get_stats(graph_id)

    if stats["status"] == "error":
        raise HTTPException(status_code=404, detail=stats["message"])

    return stats


@router.post("/{graph_id}/add-units")
async def add_units_to_graph(
        graph_id: str = Path(..., description="知识图谱ID"),
        unit_ids: List[str] = Body(..., description="知识单元ID列表"),
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: str = Depends(oauth2_scheme)
):
    """向知识图谱添加知识单元"""
    user = await get_current_user(token)

    # 检查所有权
    graph = await service.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")

    if graph.owner_id != user.id:
        raise HTTPException(status_code=403, detail="没有权限修改此知识图谱")

    result = await service.add_units(graph_id, unit_ids)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return {"status": "success", "added": result["added"]}


@router.post("/{graph_id}/add-triples")
async def add_triples_to_graph(
        graph_id: str = Path(..., description="知识图谱ID"),
        triple_ids: List[str] = Body(..., description="三元组ID列表"),
        service: KnowledgeGraphService = Depends(get_graph_service),
        token: str = Depends(oauth2_scheme)
):
    """向知识图谱添加语义三元组"""
    user = await get_current_user(token)

    # 检查所有权
    graph = await service.get(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail="知识图谱不存在")

    if graph.owner_id != user.id:
        raise HTTPException(status_code=403, detail="没有权限修改此知识图谱")

    result = await service.add_triples(graph_id, triple_ids)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return {"status": "success", "added": result["added"]}