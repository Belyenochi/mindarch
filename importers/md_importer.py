# importers/md_importer.py
import re
from typing import Dict, List, Any, Optional, Tuple
from importers.base import BaseImporter


class MarkdownImporter(BaseImporter):
    """Markdown文件导入器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ["md", "markdown"]

    async def extract_structure(self, file_name: str, content: bytes) -> Dict[str, Any]:
        """从Markdown文件提取结构"""
        text = content.decode('utf-8', errors='replace')

        # 提取元数据
        metadata, text = self._extract_frontmatter(text)
        file_metadata = self._extract_metadata(file_name)
        # 合并文件名元数据和frontmatter元数据
        metadata.update({k: v for k, v in file_metadata.items() if k not in metadata})

        # 提取章节
        sections = self._extract_sections(text)

        return {
            "metadata": metadata,
            "sections": sections
        }

    async def parse_content(self, content_structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Markdown结构为知识单元"""
        metadata = content_structure.get("metadata", {})
        sections = content_structure.get("sections", [])

        knowledge_units = []

        # 处理每个章节
        for i, section in enumerate(sections):
            section_title = section.get("title", "")
            section_content = section.get("content", "")
            section_level = section.get("level", 1)

            # 如果没有标题，使用序号和源文件名
            if not section_title:
                section_title = f"{metadata.get('title', 'Section')} - Part {i + 1}"

            # 提取标签
            tags = []
            if "tags" in metadata:
                if isinstance(metadata["tags"], list):
                    tags.extend(metadata["tags"])
                elif isinstance(metadata["tags"], str):
                    tags.append(metadata["tags"])

            content_tags = self._extract_tags(section_content)
            tags.extend(content_tags)

            # 去重
            tags = list(set(tags))

            # 创建知识单元
            unit = {
                "title": section_title[:50],  # 限制标题长度
                "content": section_content,
                "unit_type": "note",
                "source": {
                    "file_name": metadata.get("source", ""),
                    "position": i,
                    "section": section_title
                },
                "tags": tags,
                "knowledge": {
                    "importance": 5 - min(section_level, 4)  # 标题级别越小越重要
                }
            }

            knowledge_units.append(unit)

        return knowledge_units

    def _extract_frontmatter(self, text: str) -> Tuple[Dict[str, Any], str]:
        """提取YAML格式的Frontmatter"""
        metadata = {}

        # 检查是否有YAML frontmatter (---开头和结尾)
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', text, re.DOTALL)
        if frontmatter_match:
            frontmatter_text = frontmatter_match.group(1)
            text = text[frontmatter_match.end():]

            # 解析YAML
            try:
                import yaml
                metadata = yaml.safe_load(frontmatter_text)
                if not isinstance(metadata, dict):
                    metadata = {}
            except:
                pass  # 如果解析失败，使用空元数据

        return metadata, text

    def _extract_sections(self, text: str) -> List[Dict[str, Any]]:
        """根据Markdown标题提取章节"""
        lines = text.split('\n')
        sections = []
        current_section = None
        current_content = []

        for line in lines:
            # 检查是否是标题行
            header_match = re.match(r'^(#+)\s+(.+)$', line)

            if header_match:
                # 如果已有章节，保存它
                if current_section is not None:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                # 创建新章节
                level = len(header_match.group(1))
                title = header_match.group(2).strip()

                current_section = {
                    "title": title,
                    "level": level,
                    "content": ""
                }
                current_content = []
            else:
                current_content.append(line)

        # 保存最后一个章节
        if current_section is not None:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)
        elif current_content:
            # 如果没有标题但有内容，创建默认章节
            sections.append({
                "title": "",
                "level": 1,
                "content": "\n".join(current_content).strip()
            })

        # 如果没有找到章节，创建一个包含全部内容的默认章节
        if not sections and text.strip():
            sections.append({
                "title": "",
                "level": 1,
                "content": text.strip()
            })

        return sections

    def _extract_tags(self, content: str) -> List[str]:
        """从Markdown内容中提取标签"""
        tags = []

        # 查找Markdown标签模式: #tag
        for match in re.finditer(r'(?<!\S)#([a-zA-Z0-9_\u4e00-\u9fa5][a-zA-Z0-9_\u4e00-\u9fa5-]*)', content):
            tag = match.group(1).strip()
            if tag and not tag.isdigit() and len(tag) < 20:
                tags.append(tag)

        # 查找[tag](tag链接)模式
        for match in re.finditer(r'\[([^\[\]]+)\]\([^\(\)]+\)', content):
            tag = match.group(1).strip()
            if tag and len(tag) < 20:
                tags.append(tag)

        # 保留前10个标签
        return tags[:10]