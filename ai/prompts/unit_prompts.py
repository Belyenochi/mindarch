# ai/prompts/unit_prompts.py
from typing import List


class UnitPrompts:
    """知识单元提取和增强的提示模板"""

    def get_extraction_prompt(self, text: str) -> str:
        """获取知识单元提取提示"""
        return f"""
        # ai/prompts/unit_prompts.py (continued)
        请从以下文本中提取关键的知识单元。每个知识单元应该是一个独立的信息点、概念或主题。
        
        分析文本：
        {text}
        
        对每个知识单元，请提供以下信息：
        1. 标题（20字以内的简洁概括）
        2. 内容（完整的知识描述）
        3. 标签（关键词，用于分类）
        4. 单元类型（note-笔记, concept-概念, entity-实体, process-过程, etc.）
        
        以JSON格式返回结果：
        {{
            "units": [
                {{
                    "title": "知识单元1标题",
                    "content": "知识单元1的完整内容描述",
                    "tags": ["标签1", "标签2", "标签3"],
                    "unit_type": "concept"
                }},
                {{
                    "title": "知识单元2标题",
                    "content": "知识单元2的完整内容描述",
                    "tags": ["标签1", "标签4"],
                    "unit_type": "entity"
                }},
                // 可能有更多知识单元...
            ]
        }}
        
        请确保：
        - 每个知识单元的内容完整且有意义
        - 标题简洁明了，能准确概括内容
        - 标签反映核心概念和分类
        - 单元类型准确
        - 仅返回JSON格式，不要有其他说明文字
        """

    def get_enhancement_prompt(self, title: str, content: str, tags: List[str]) -> str:
        """获取知识单元增强提示"""
        tags_str = ", ".join(tags) if tags else "无标签"

        return f"""
        请分析以下知识单元，并提供增强信息以便更好地将其整合到知识图谱中。
        
        知识单元标题：
        {title}
        
        知识单元内容：
        {content}
        
        现有标签：
        {tags_str}
        
        请提供以下增强信息：
        
        1. 规范名称(canonical_name)：作为唯一标识符的英文名称，使用下划线连接
        2. 别名(aliases)：该知识的其他常用称呼
        3. 补充标签(tags)：更完整的标签集合
        4. 知识领域(domain)：所属的主要知识领域
        5. 实体类型(entity_type)：更精确的类型分类
        6. 重要性(importance)：1-5分，表示在领域内的重要程度
        7. 抽象级别(abstraction_level)：1-5分，1表示具体实例，5表示高度抽象概念
        8. 属性(properties)：该知识单元的关键属性，以键值对形式
        9. 完整度评分(completeness)：0-1分，表示内容的完整程度
        
        以JSON格式返回：
        {{
            "canonical_name": "规范名称",
            "aliases": ["别名1", "别名2"],
            "tags": ["标签1", "标签2", "标签3"],
            "domain": "知识领域",
            "entity_type": "实体类型",
            "importance": 数字(1-5),
            "abstraction_level": 数字(1-5),
            "properties": {{
                "属性1": "值1",
                "属性2": "值2"
            }},
            "completeness": 数字(0-1)
        }}
        
        仅返回JSON格式，不要有其他说明文字。
        """