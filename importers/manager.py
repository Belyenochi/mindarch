# importers/manager.py
import os
import tempfile
from typing import Dict, List, Any, Optional, BinaryIO
from datetime import datetime
import uuid
import asyncio

from loguru import logger
from core.config import settings
from importers.txt_importer import TxtImporter
from importers.md_importer import MarkdownImporter
from ai.extraction.unit_extractor import KnowledgeUnitExtractor
from ai.extraction.relation_extractor import RelationExtractor
from core.services.knowledge_unit import KnowledgeUnitService
from core.services.semantic_triple import SemanticTripleService
from core.services.knowledge_graph import KnowledgeGraphService


class ImportManager:
    """导入管理器，协调整个导入流程"""

    def __init__(self):
        """初始化导入管理器"""
        self.importers = {
            "txt": TxtImporter(),
            "md": MarkdownImporter(),
            "markdown": MarkdownImporter()
        }
        self.unit_extractor = KnowledgeUnitExtractor()
        self.relation_extractor = RelationExtractor()
        self.unit_service = KnowledgeUnitService()
        self.triple_service = SemanticTripleService()
        self.graph_service = KnowledgeGraphService()

        # 进行中的导入任务
        self.active_imports = {}

    async def import_file(self, file_name: str, content: bytes, file_type: str,
                          owner_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """导入文件并启动处理流程"""
        # 获取合适的导入器
        if file_type not in self.importers:
            return {"status": "error", "message": f"不支持的文件类型: {file_type}"}

        importer = self.importers[file_type]

        # 计算文件哈希
        file_hash = importer.calculate_hash(content)

        # 检查是否已存在相同文件
        duplicate = await self._check_duplicate(file_hash, owner_id)
        if duplicate:
            return {"status": "duplicate", "import_id": duplicate}

        # 创建导入记录
        import_id = str(uuid.uuid4())

        # 记录导入任务
        self.active_imports[import_id] = {
            "id": import_id,
            "file_name": file_name,
            "file_type": file_type,
            "file_size": len(content),
            "file_hash": file_hash,
            "owner_id": owner_id,
            "status": "pending",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "options": options or {},
            "progress": 0
        }

        # 异步启动处理
        asyncio.create_task(self._process_file(import_id, file_name, content, file_type, options))

        return {"status": "processing", "import_id": import_id}

    async def get_import_status(self, import_id: str) -> Optional[Dict[str, Any]]:
        """获取导入状态"""
        if import_id in self.active_imports:
            return self.active_imports[import_id]

        # 查找历史导入
        import_record = await self._find_import_record(import_id)
        return import_record

    async def get_import_history(self, query: Dict[str, Any], limit: int = 20,
                                 skip: int = 0) -> List[Dict[str, Any]]:
        """获取导入历史"""
        # 在这里实现导入历史查询
        # 可以是临时的内存存储或简单的文件存储
        # 在MVP阶段可以简化为仅返回活动导入
        active = [imp for imp in self.active_imports.values()
                  if all(imp.get(k) == v for k, v in query.items())]

        # 对结果排序和分页
        active.sort(key=lambda x: x["created_at"], reverse=True)
        return active[skip:skip + limit]

    async def count_imports(self, query: Dict[str, Any]) -> int:
        """计数导入记录"""
        # 简化实现
        active_count = len([imp for imp in self.active_imports.values()
                            if all(imp.get(k) == v for k, v in query.items())])
        return active_count

    async def cancel_import(self, import_id: str) -> Dict[str, Any]:
        """取消导入任务"""
        if import_id not in self.active_imports:
            return {"status": "error", "message": "导入任务不存在"}

        import_task = self.active_imports[import_id]

        if import_task["status"] not in ["pending", "processing"]:
            return {"status": "error", "message": "无法取消已完成的任务"}

        # 更新状态
        import_task["status"] = "cancelled"
        import_task["updated_at"] = datetime.now()

        return {"status": "success"}

    async def delete_import(self, import_id: str) -> Dict[str, Any]:
        """删除导入记录"""
        if import_id in self.active_imports:
            # 如果任务正在进行，先取消
            if self.active_imports[import_id]["status"] in ["pending", "processing"]:
                await self.cancel_import(import_id)

            # 删除记录
            del self.active_imports[import_id]

        return {"status": "success"}

    async def _process_file(self, import_id: str, file_name: str, content: bytes,
                            file_type: str, options: Optional[Dict[str, Any]] = None):
        """处理文件的完整流程"""
        try:
            # 更新状态
            self._update_import_status(import_id, "processing", 5)

            # 使用导入器提取结构
            importer = self.importers[file_type]
            import_result = await importer.import_file(file_name, content)

            # 提取初步知识单元
            self._update_import_status(import_id, "processing", 20)
            raw_units = import_result.get("units", [])

            # 使用AI增强知识单元
            self._update_import_status(import_id, "processing", 40)
            enhanced_units = await self.unit_extractor.process_units(raw_units)

            # 保存知识单元
            self._update_import_status(import_id, "processing", 60)
            unit_ids = await self._save_units(enhanced_units, import_id, file_name)

            # 提取关系
            self._update_import_status(import_id, "processing", 75)
            relations = await self.relation_extractor.extract_relations(enhanced_units, unit_ids)

            # 保存关系
            self._update_import_status(import_id, "processing", 85)
            relation_ids = await self._save_relations(relations)

            # 创建知识图谱
            self._update_import_status(import_id, "processing", 95)
            graph_id = await self._create_graph(file_name, unit_ids, relation_ids, import_id,
                                                self.active_imports[import_id]["owner_id"])

            # 更新导入状态为完成
            self._update_import_status(
                import_id,
                "completed",
                100,
                {
                    "unit_count": len(unit_ids),
                    "relation_count": len(relation_ids),
                    "graph_id": graph_id,
                    "processing_end": datetime.now()
                }
            )

        except Exception as e:
            logger.error(f"处理文件失败: {str(e)}")

            # 更新导入状态为失败
            self._update_import_status(
                import_id,
                "failed",
                100,
                {
                    "error": str(e),
                    "processing_end": datetime.now()
                }
            )

    def _update_import_status(self, import_id: str, status: str, progress: int,
                              additional_data: Optional[Dict[str, Any]] = None):
        """更新导入任务状态"""
        if import_id in self.active_imports:
            import_task = self.active_imports[import_id]
            import_task["status"] = status
            import_task["progress"] = progress
            import_task["updated_at"] = datetime.now()

            if additional_data:
                import_task.update(additional_data)

    async def _check_duplicate(self, file_hash: str, owner_id: str) -> Optional[str]:
        """检查是否存在相同文件"""
        # 在活动导入中查找
        for import_id, task in self.active_imports.items():
            if task["file_hash"] == file_hash and task["owner_id"] == owner_id:
                return import_id

        # 在历史导入中查找
        # 简化MVP实现，仅检查活动导入
        return None

    async def _find_import_record(self, import_id: str) -> Optional[Dict[str, Any]]:
        """查找导入记录"""
        # 简化MVP实现，仅查找活动导入
        return self.active_imports.get(import_id)

    async def _save_units(self, units: List[Dict[str, Any]], import_id: str,
                          file_name: str) -> List[str]:
        """保存知识单元并返回ID列表"""
        unit_ids = []

        for unit in units:
            # 设置导入相关信息
            if "source" not in unit:
                unit["source"] = {}

            unit["source"]["import_id"] = import_id
            unit["source"]["file_name"] = file_name

            # 保存单元
            result = await self.unit_service.create(unit)

            if result["status"] == "success":
                unit_ids.append(result["unit_id"])

        return unit_ids

    async def _save_relations(self, relations: List[Dict[str, Any]]) -> List[str]:
        """保存关系并返回ID列表"""
        relation_ids = []

        for relation in relations:
            # 保存关系
            result = await self.triple_service.create(relation)

            if result["status"] == "success":
                relation_ids.append(result["triple_id"])

        return relation_ids

    async def _create_graph(self, file_name: str, unit_ids: List[str], relation_ids: List[str],
                            import_id: str, owner_id: str) -> str:
        """创建知识图谱"""
        # 准备图谱数据
        graph_name = os.path.splitext(file_name)[0]

        graph_data = {
            "name": graph_name,
            "description": f"从{file_name}导入的知识图谱",
            "owner_id": owner_id,
            "is_public": False,
            "included_units": unit_ids,
            "included_triples": relation_ids,
            "metadata": {
                "source": "file_import",
                "import_id": import_id,
                "file_name": file_name
            }
        }

        # 创建图谱
        result = await self.graph_service.create(graph_data)

        if result["status"] == "success":
            return result["graph_id"]
        else:
            raise Exception(f"创建知识图谱失败: {result.get('message', '')}")