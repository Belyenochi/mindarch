# importers/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import hashlib


class BaseImporter(ABC):
    """导入器基类，定义通用方法与接口"""

    def __init__(self):
        """初始化导入器"""
        self.supported_extensions = []

    def can_handle(self, file_type: str) -> bool:
        """检查是否支持此文件类型"""
        return file_type.lower() in self.supported_extensions

    def calculate_hash(self, content: bytes) -> str:
        """计算内容哈希，用于重复检测"""
        return hashlib.md5(content).hexdigest()

    @abstractmethod
    async def extract_structure(self, file_name: str, content: bytes) -> Dict[str, Any]:
        """从文件内容中提取结构化数据"""
        pass

    @abstractmethod
    async def parse_content(self, content_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析结构化数据为知识单元"""
        pass

    async def import_file(self, file_name: str, content: bytes) -> Dict[str, Any]:
        """导入文件的完整流程"""
        # 提取结构
        content_structure = await self.extract_structure(file_name, content)

        # 解析为知识单元
        knowledge_units = await self.parse_content(content_structure)

        return {
            "file_name": file_name,
            "hash": self.calculate_hash(content),
            "units": knowledge_units
        }

    def _extract_metadata(self, file_name: str) -> Dict[str, Any]:
        """从文件名提取元数据"""
        parts = file_name.split('.')
        name = '.'.join(parts[:-1]) if len(parts) > 1 else file_name

        return {
            "title": name.replace('_', ' ').replace('-', ' ').title(),
            "source": file_name
        }