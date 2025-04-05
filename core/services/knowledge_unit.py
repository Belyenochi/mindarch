# core/services/knowledge_unit.py
from typing import Dict, List, Optional, Any
from datetime import datetime
from bson import ObjectId

from db.repositories.knowledge_unit_repo import KnowledgeUnitRepository
from core.models.knowledge_unit import KnowledgeUnit


class KnowledgeUnitService:
    """知识单元服务"""

    def __init__(self):
        self.repository = KnowledgeUnitRepository()

    async def create(self, unit_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新的知识单元"""
        # 数据验证
        self._validate_unit_data(unit_data)

        # 生成规范名称
        if not unit_data.get("canonical_name"):
            unit_data["canonical_name"] = self._generate_canonical_name(unit_data.get("title", ""))

        # 检查是否存在重复
        duplicate = await self._find_duplicate(unit_data["canonical_name"])
        if duplicate:
            return {"status": "duplicate", "duplicate_id": str(duplicate.id)}

        # 准备创建数据
        if "created_at" not in unit_data:
            unit_data["created_at"] = datetime.now()
        if "updated_at" not in unit_data:
            unit_data["updated_at"] = datetime.now()

        # 创建知识单元
        unit = KnowledgeUnit(**unit_data)
        result = await self.repository.create(unit)

        return {"status": "success", "unit_id": str(result.id)}

    async def get(self, unit_id: str) -> Optional[KnowledgeUnit]:
        """获取单个知识单元"""
        unit = await self.repository.get_by_id(unit_id)
        if unit:
            # 更新查看计数
            await self.repository.increment_view_count(unit_id)
        return unit

    async def update(self, unit_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新知识单元"""
        # 验证单元存在
        existing = await self.repository.get_by_id(unit_id)
        if not existing:
            return {"status": "error", "message": "知识单元不存在"}

        # 准备更新数据
        update_data["updated_at"] = datetime.now()

        # 执行更新
        result = await self.repository.update(unit_id, update_data)

        return {
            "status": "success",
            "matched": result.matched_count,
            "modified": result.modified_count
        }

    async def delete(self, unit_id: str) -> Dict[str, Any]:
        """删除知识单元"""
        # 验证单元存在
        existing = await self.repository.get_by_id(unit_id)
        if not existing:
            return {"status": "error", "message": "知识单元不存在"}

        # 执行删除
        result = await self.repository.delete(unit_id)

        return {
            "status": "success",
            "deleted": result.deleted_count
        }

    async def find(self, query: Dict[str, Any], limit: int = 20,
                   skip: int = 0, sort: Optional[List] = None) -> List[KnowledgeUnit]:
        """查找知识单元"""
        return await self.repository.find(query, limit, skip, sort)

    async def count(self, query: Dict[str, Any]) -> int:
        """计数查询结果"""
        return await self.repository.count(query)

    async def search(self, text_query: str, filters: Optional[Dict[str, Any]] = None,
                     limit: int = 20, skip: int = 0) -> List[KnowledgeUnit]:
        """全文搜索知识单元"""
        return await self.repository.search(text_query, filters, limit, skip)

    async def count_search(self, text_query: str, filters: Optional[Dict[str, Any]] = None) -> int:
        """计数搜索结果"""
        return await self.repository.count_search(text_query, filters)

    async def merge(self, primary_id: str, secondary_ids: List[str]) -> Dict[str, Any]:
        """合并多个知识单元"""
        # 验证主要单元存在
        primary = await self.repository.get_by_id(primary_id)
        if not primary:
            return {"status": "error", "message": "主要单元不存在"}

        # 获取次要单元
        secondary_units = []
        for sec_id in secondary_ids:
            unit = await self.repository.get_by_id(sec_id)
            if unit:
                secondary_units.append(unit)

        if not secondary_units:
            return {"status": "error", "message": "没有有效的次要单元"}

        # 合并信息
        merged = await self._merge_unit_data(primary, secondary_units)

        # 更新主要单元
        update_result = await self.repository.update(primary_id, merged)

        # 更新次要单元状态
        for unit in secondary_units:
            await self.repository.update(
                str(unit.id),
                {
                    "status": {"state": "merged"},
                    "merged_into": primary_id,
                    "updated_at": datetime.now()
                }
            )

        return {"status": "success", "primary_id": primary_id}

    async def bulk_create(self, units: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量创建知识单元"""
        unit_objects = []

        for unit_data in units:
            # 数据验证
            self._validate_unit_data(unit_data)

            # 生成规范名称
            if not unit_data.get("canonical_name"):
                unit_data["canonical_name"] = self._generate_canonical_name(unit_data.get("title", ""))

            # 准备创建数据
            if "created_at" not in unit_data:
                unit_data["created_at"] = datetime.now()
            if "updated_at" not in unit_data:
                unit_data["updated_at"] = datetime.now()

            unit = KnowledgeUnit(**unit_data)
            unit_objects.append(unit)

        if not unit_objects:
            return {"status": "error", "message": "没有有效的单元数据"}

        # 批量创建
        result = await self.repository.bulk_insert(unit_objects)

        return {
            "status": "success",
            "created": len(result),
            "unit_ids": [str(unit.id) for unit in result]
        }

    # 内部辅助方法

    def _validate_unit_data(self, data: Dict[str, Any]) -> None:
        """验证知识单元数据"""
        if not data.get("title"):
            raise ValueError("知识单元必须有标题")

        # 标题长度限制
        if "title" in data and len(data["title"]) > 100:
            data["title"] = data["title"][:100]

    async def _find_duplicate(self, canonical_name: str) -> Optional[KnowledgeUnit]:
        """查找是否存在重复的知识单元"""
        return await self.repository.find_one({"canonical_name": canonical_name})

    def _generate_canonical_name(self, title: str) -> str:
        """根据标题生成规范名称"""
        # 移除特殊字符，转换为小写，用下划线替换空格
        import re
        name = re.sub(r'[^\w\s]', '', title.lower())
        name = re.sub(r'\s+', '_', name.strip())

        # 处理中文
        if re.search(r'[\u4e00-\u9fff]', name):
            # 对于中文标题，使用拼音
            try:
                from pypinyin import lazy_pinyin
                name = '_'.join(lazy_pinyin(name))
            except ImportError:
                # 如果没有pypinyin库，简单处理
                name = re.sub(r'[\u4e00-\u9fff]', '', name)
                name = re.sub(r'_+', '_', name)
                if not name:
                    # 如果处理后为空，使用时间戳
                    name = f"unit_{int(datetime.now().timestamp())}"

        # 长度限制
        if len(name) > 50:
            name = name[:50]

        # 确保不为空
        if not name:
            name = f"unit_{int(datetime.now().timestamp())}"

        return name

    async def _merge_unit_data(self, primary: KnowledgeUnit, secondary: List[KnowledgeUnit]) -> Dict[str, Any]:
        """合并多个知识单元的数据"""
        merged = {}

        # 合并标题可选
        # merged["title"] = primary.title

        # 合并内容
        contents = [primary.content]
        for unit in secondary:
            if unit.content.strip():
                contents.append(f"--- 从 {unit.title} 合并 ---\n{unit.content}")
        merged["content"] = "\n\n".join(contents)

        # 合并别名
        aliases = set(primary.aliases)
        for unit in secondary:
            aliases.update(unit.aliases)
            aliases.add(unit.title)  # 将次要单元的标题添加为主要单元的别名
        merged["aliases"] = list(aliases)

        # 合并标签
        tags = set(primary.tags)
        for unit in secondary:
            tags.update(unit.tags)
        merged["tags"] = list(tags)

        # 记录合并的单元
        merged_units = set(primary.merged_units)
        for unit in secondary:
            merged_units.add(str(unit.id))
            merged_units.update(unit.merged_units)
        merged["merged_units"] = list(merged_units)

        # 更新时间
        merged["updated_at"] = datetime.now()

        return merged