# api/routes/file_imports.py
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from importers.manager import ImportManager
from services.auth import get_current_user


# 内部定义必要的响应模型，不依赖外部schema
class FileImportResponse(BaseModel):
    status: str
    import_id: str


class FileImportStatus(BaseModel):
    id: str
    file_name: str
    file_type: str
    status: str
    status_description: Optional[str] = None
    progress: int
    created_at: Any
    updated_at: Any
    owner_id: str
    current_phase: Optional[str] = None
    options: Dict[str, Any] = {}
    error: Optional[str] = None
    unit_count: Optional[int] = None
    relation_count: Optional[int] = None
    graph_id: Optional[str] = None


class FileImportList(BaseModel):
    items: List[FileImportStatus]
    total: int
    limit: int
    skip: int


router = APIRouter(prefix="/import", tags=["文件导入"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


# 依赖注入
def get_import_manager():
    return ImportManager()


@router.post("/", response_model=FileImportResponse, status_code=202)
async def import_file(
        file: UploadFile = File(...),
        options: Optional[str] = Form(None),
        manager: ImportManager = Depends(get_import_manager),
        token: str = Depends(oauth2_scheme)
):
    """导入文件并启动处理流程"""
    user = await get_current_user(token)

    try:
        # 检查文件类型
        file_type = file.filename.split('.')[-1].lower()
        if file_type not in ["txt", "md"]:
            raise HTTPException(status_code=415, detail="不支持的文件类型")

        # 读取文件元数据来检查大小
        if hasattr(file, "size") and file.size > 1 * 1024 * 1024:  # 1MB
            raise HTTPException(status_code=413, detail="文件太大")

        # 读取文件内容
        content = await file.read()

        # 如果file对象没有size属性，使用内容长度检查
        if not hasattr(file, "size") and len(content) > 1 * 1024 * 1024:  # 1MB
            # 重置文件位置以允许再次读取
            await file.seek(0)
            raise HTTPException(status_code=413, detail="文件太大")

        # 处理选项
        options_dict = {}
        if options:
            import json
            try:
                options_dict = json.loads(options)
            except:
                raise HTTPException(status_code=400, detail="选项格式无效")

        # 导入文件
        result = await manager.import_file(
            file.filename,
            content,
            file_type,
            user.id,
            options_dict
        )

        if result["status"] == "duplicate":
            raise HTTPException(status_code=409, detail="文件已存在")

        return {"status": "processing", "import_id": result["import_id"]}

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.get("/{import_id}", response_model=FileImportStatus)
async def get_import_status(
        import_id: str = Path(..., description="导入记录ID"),
        manager: ImportManager = Depends(get_import_manager),
        token: str = Depends(oauth2_scheme)
):
    """获取导入状态"""
    user = await get_current_user(token)

    import_status = await manager.get_import_status(import_id)

    if not import_status:
        raise HTTPException(status_code=404, detail="导入记录不存在")

    if import_status["owner_id"] != user.id:
        raise HTTPException(status_code=403, detail="没有权限查看此导入记录")

    return import_status


@router.get("/", response_model=FileImportList)
async def get_import_history(
        limit: int = Query(20, ge=1, le=100),
        skip: int = Query(0, ge=0),
        status: Optional[str] = Query(None),
        manager: ImportManager = Depends(get_import_manager),
        token: str = Depends(oauth2_scheme)
):
    """获取导入历史"""
    user = await get_current_user(token)

    query = {"owner_id": user.id}
    if status:
        query["status"] = status

    imports = await manager.get_import_history(query, limit, skip)
    total = await manager.count_imports(query)

    return {
        "items": imports,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.delete("/{import_id}", status_code=204)
async def delete_import(
        import_id: str = Path(..., description="导入记录ID"),
        manager: ImportManager = Depends(get_import_manager),
        token: str = Depends(oauth2_scheme)
):
    """删除导入记录"""
    user = await get_current_user(token)

    import_record = await manager.get_import_status(import_id)

    if not import_record:
        raise HTTPException(status_code=404, detail="导入记录不存在")

    if import_record["owner_id"] != user.id:
        raise HTTPException(status_code=403, detail="没有权限删除此导入记录")

    result = await manager.delete_import(import_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return None


@router.post("/{import_id}/cancel", response_model=Dict[str, str])
async def cancel_import(
        import_id: str = Path(..., description="导入记录ID"),
        manager: ImportManager = Depends(get_import_manager),
        token: str = Depends(oauth2_scheme)
):
    """取消导入任务"""
    user = await get_current_user(token)

    import_record = await manager.get_import_status(import_id)

    if not import_record:
        raise HTTPException(status_code=404, detail="导入记录不存在")

    if import_record["owner_id"] != user.id:
        raise HTTPException(status_code=403, detail="没有权限取消此导入任务")

    if import_record["status"] not in ["pending", "processing"]:
        raise HTTPException(status_code=400, detail="只能取消待处理或处理中的任务")

    result = await manager.cancel_import(import_id)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return {"status": "cancelled"}