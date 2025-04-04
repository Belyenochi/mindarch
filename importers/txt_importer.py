# importers/txt_importer.py
import re
from typing import Dict, List, Any, Optional, Tuple
from importers.base import BaseImporter


class TxtImporter(BaseImporter):
    """TXT文件导入器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ["txt"]

    async def extract_structure(self, file_name: str, content: bytes) -> Dict[str, Any]:
        """从TXT文件提取结构"""
        text = content.decode('utf-8', errors='replace')

        # 提取元数据
        metadata = self._extract_metadata(file_name)

        # 分段
        sections = self._split_into_sections(text)

        return {
            "metadata": metadata,
            "sections": sections
        }

    async def parse_content(self, content_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析TXT结构为知识单元"""
        metadata = content_structure.get("metadata", {})
        sections = content_structure.get("sections", [])

        knowledge_units = []

        # 处理每个部分
        for i, section in enumerate(sections):
            # 提取标题和内容
            title, content = self._extract_title_and_content(section)

            # 如果没有标题，使用序号和源文件名
            if not title:
                title = f"{metadata.get('title', 'Section')} - Part {i + 1}"

            # 创建知识单元
            unit = {
                "title": title[:50],  # 限制标题长度
                "content": content,
                "unit_type": "note",
                "source": {
                    "file_name": metadata.get("source", ""),
                    "position": i,
                    "section": ""
                },
                "tags": self._extract_tags(content)
            }

            knowledge_units.append(unit)

        return knowledge_units

    def _split_into_sections(self, text: str) -> List[str]:
        """将文本分割为段落或章节"""
        # 移除多余的空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # 检查是否有明确的章节分隔符
        section_markers = [
            r'(?:\n|^)#+\s+.+\n',  # Markdown风格标题
            r'(?:\n|^)第\s*[一二三四五六七八九十\d]+\s*[章节篇部]\s*\S+\n',  # 中文章节标题
            r'(?:\n|^)Chapter\s+\d+.*\n',  # 英文章节标题
            r'(?:\n|^)\d+\.\s+\S+\n'  # 编号标题
        ]

        for marker in section_markers:
            if re.search(marker, text):
                return self._split_by_headers(text, marker)

        # 如果没有明确的分隔符，按双空行分段
        sections = re.split(r'\n\n+', text)

        # 移除空段落
        sections = [s.strip() for s in sections if s.strip()]

        # 如果段落太多，尝试合并相邻的短段落
        if len(sections) > 20:
            sections = self._merge_short_sections(sections)

        return sections

    def _split_by_headers(self, text: str, marker: str) -> List[str]:
        """按标题分割文本"""
        split_positions = [0]

        for match in re.finditer(marker, text):
            if match.start() > 0:
                split_positions.append(match.start())

        # 添加文本结尾
        split_positions.append(len(text))

        # 按位置分割
        sections = []
        for i in range(len(split_positions) - 1):
            start = split_positions[i]
            end = split_positions[i + 1]
            section = text[start:end].strip()
            if section:
                sections.append(section)

        return sections

    def _merge_short_sections(self, sections: List[str], min_length: int = 200) -> List[str]:
        """合并短段落"""
        result = []
        current = []
        current_length = 0

        for section in sections:
            if current_length + len(section) < min_length:
                current.append(section)
                current_length += len(section)
            else:
                if current:
                    result.append("\n\n".join(current))
                    current = []
                    current_length = 0

                if len(section) < min_length:
                    current.append(section)
                    current_length = len(section)
                else:
                    result.append(section)

        if current:
            result.append("\n\n".join(current))

        return result

    def _extract_title_and_content(self, section: str) -> Tuple[str, str]:
        """从段落提取标题和内容"""
        lines = section.split('\n')

        # 检查第一行是否像标题
        if lines and (
                re.match(r'^#+\s+', lines[0]) or  # Markdown标题
                re.match(r'^第\s*[一二三四五六七八九十\d]+\s*[章节篇部]', lines[0]) or  # 中文章节标题
                re.match(r'^Chapter\s+\d+', lines[0]) or  # 英文章节标题
                re.match(r'^\d+\.\s+', lines[0]) or  # 编号标题
                (len(lines) > 1 and len(lines[0]) < 100 and lines[1].strip() == '')  # 短行后接空行
        ):
            # 提取标题并清理
            title = lines[0].strip()
            title = re.sub(r'^#+\s+', '', title)  # 移除Markdown标记
            title = re.sub(r'^\d+\.\s+', '', title)  # 移除编号

            # 内容为剩余行
            content = '\n'.join(lines[1:]).strip()

            return title, content

        # 如果没有明确标题，尝试使用第一句话
        if lines:
            first_line = lines[0].strip()
            if len(first_line) < 100 and '。' in first_line:
                title = first_line.split('。')[0] + '。'
                return title, section

        # 如果无法提取标题，返回空标题和完整内容
        return "", section

    def _extract_tags(self, content: str) -> List[str]:
        """尝试从内容中提取标签"""
        tags = []

        # 查找常见标签模式
        # 例如 #标签# 或 [标签] 或 【标签】
        tag_patterns = [
            r'#([^#\s]+)#',
            r'\[([^\[\]\s]+)\]',
            r'【([^【】\s]+)】'
        ]

        for pattern in tag_patterns:
            for match in re.finditer(pattern, content):
                tag = match.group(1).strip()
                if tag and len(tag) < 20:
                    tags.append(tag)

        # 保留前10个标签
        return tags[:10]