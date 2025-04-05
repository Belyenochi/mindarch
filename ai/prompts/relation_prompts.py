# ai/prompts/relation_prompts.py

class RelationPrompts:
    """关系提取的提示模板"""

    def get_relation_extraction_prompt(self, subject_title: str, subject_content: str,
                                       object_title: str, object_content: str) -> str:
        """获取关系提取提示"""
        return f"""
        请分析以下两个知识单元，确定它们之间可能存在的语义关系。

        知识单元A：
        标题：{subject_title}
        内容：{subject_content}

        知识单元B：
        标题：{object_title}
        内容：{object_content}

        请考虑这两个知识单元之间的各种可能关系，例如：
        - 分类关系（A是B的一种）
        - 组成关系（A是B的一部分）
        - 属性关系（A具有属性B）
        - 因果关系（A导致B）
        - 先后关系（A先于B）
        - 相似关系（A类似于B）
        - 位置关系（A位于B）
        - 用途关系（A用于B）
        - 其他关系

        以JSON格式返回所有可能的关系：
        {{
            "relations": [
                {{
                    "predicate": "关系描述（例如：是一种、包含、导致等）",
                    "relation_type": "关系类型（例如：is_a, part_of, causes等）",
                    "bidirectional": true/false,
                    "confidence": 0-1之间的数字,
                    "context": "支持这种关系判断的上下文或依据"
                }},
                // 可能有多个关系...
            ]
        }}

        请确保：
        - 每个关系的predicate是准确描述两个单元关系的短语
        - relation_type使用标准化分类
        - 仅在确实存在双向关系时设置bidirectional为true
        - confidence表示该关系判断的可信度
        - 尽可能多地发现有意义的关系，但不要强行建立不存在的关系
        - 仅返回JSON格式，不要有其他说明文字
        """

    def get_batch_relation_prompt(self, unit_summaries: list) -> str:
        """获取批量关系提取提示"""
        units_text = "\n\n".join([
            f"单元{i}：\n标题: {unit['title']}\n内容摘要: {unit['summary']}"
            for i, unit in enumerate(unit_summaries)
        ])

        return f"""
        请分析以下知识单元列表，确定它们之间可能存在的语义关系。

        知识单元列表：
        {units_text}

        分析这些知识单元之间可能存在的关系，并以JSON格式返回：
        {{
            "relations": [
                {{
                    "subject_id": 起始单元的编号,
                    "object_id": 目标单元的编号,
                    "predicate": "关系描述",
                    "relation_type": "关系类型",
                    "bidirectional": true/false,
                    "confidence": 0-1之间的数字
                }},
                // 可能有多个关系...
            ]
        }}

        请确保：
        - subject_id和object_id对应上面的单元编号
        - 每个关系是有意义的，不要强行建立不存在的关系
        - 仅返回JSON格式，不要有其他说明文字
        """