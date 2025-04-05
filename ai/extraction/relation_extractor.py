# ai/extraction/relation_extractor.py
from typing import Dict, List, Any, Optional
import asyncio
from bson import ObjectId

from loguru import logger
from ai.client import OpenAIClient
from ai.prompts.relation_prompts import RelationPrompts
from ai.evaluation.confidence import ConfidenceEvaluator


class RelationExtractor:
    """关系提取器，从知识单元中提取语义关系"""

    def __init__(self, model: Optional[str] = None):
        """初始化提取器"""
        self.client = OpenAIClient(model)
        self.prompts = RelationPrompts()
        self.confidence_evaluator = ConfidenceEvaluator()
        self.batch_size = 10  # 批处理大小
        self.max_pairs = 100  # 最大处理的单元对数量

    async def extract_relations(self, units: List[Dict[str, Any]],
                                unit_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """从知识单元中提取关系"""
        if not units:
            return []

        # 如果没有提供ID，使用索引作为ID
        if not unit_ids:
            unit_ids = [str(i) for i in range(len(units))]

        # 确保单元和ID数量一致
        if len(units) != len(unit_ids):
            raise ValueError("单元列表和ID列表长度不一致")

        # 构建单元对
        unit_pairs = self._generate_unit_pairs(units, unit_ids)

        # 限制处理数量
        if len(unit_pairs) > self.max_pairs:
            logger.warning(f"单元对数量({len(unit_pairs)})超过最大限制({self.max_pairs})，将随机采样")
            import random
            random.shuffle(unit_pairs)
            unit_pairs = unit_pairs[:self.max_pairs]

        # 批量处理
        all_relations = []
        for i in range(0, len(unit_pairs), self.batch_size):
            batch = unit_pairs[i:i + self.batch_size]
            batch_results = await asyncio.gather(*[
                self._extract_pair_relations(pair) for pair in batch
            ])

            for relations in batch_results:
                all_relations.extend(relations)

        # 后处理：去重、评估置信度
        processed_relations = self._post_process(all_relations)

        return processed_relations

    def _generate_unit_pairs(self, units: List[Dict[str, Any]],
                             unit_ids: List[str]) -> List[Dict[str, Any]]:
        """生成需要处理的单元对"""
        pairs = []

        # 采用启发式方法选择可能相关的单元对
        for i in range(len(units)):
            for j in range(i + 1, len(units)):
                # 检查是否可能存在关系
                if self._may_have_relation(units[i], units[j]):
                    pairs.append({
                        "subject": {
                            "id": unit_ids[i],
                            "title": units[i].get("title", ""),
                            "content": units[i].get("content", ""),
                            "unit_type": units[i].get("unit_type", "note")
                        },
                        "object": {
                            "id": unit_ids[j],
                            "title": units[j].get("title", ""),
                            "content": units[j].get("content", ""),
                            "unit_type": units[j].get("unit_type", "note")
                        }
                    })

        return pairs

    def _may_have_relation(self, unit1: Dict[str, Any], unit2: Dict[str, Any]) -> bool:
        """判断两个单元是否可能存在关系"""
        # 简单启发式规则：
        # 1. 如果单元之间存在标签重叠
        # 2. 如果一个单元的标题出现在另一个单元的内容中
        # 3. 如果它们同属于一个领域

        # 标签重叠
        tags1 = set(unit1.get("tags", []))
        tags2 = set(unit2.get("tags", []))
        if tags1 and tags2 and tags1.intersection(tags2):
            return True

        # 标题与内容关联
        title1 = unit1.get("title", "").lower()
        title2 = unit2.get("title", "").lower()
        content1 = unit1.get("content", "").lower()
        content2 = unit2.get("content", "").lower()

        if title1 and title1 in content2:
            return True
        if title2 and title2 in content1:
            return True

        # 领域一致
        domain1 = unit1.get("knowledge", {}).get("domain", "")
        domain2 = unit2.get("knowledge", {}).get("domain", "")
        if domain1 and domain2 and domain1 == domain2:
            return True

        # 默认：基于内容相似性抽样
        return True

    async def _extract_pair_relations(self, pair: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取一对知识单元之间的关系"""
        subject = pair["subject"]
        object = pair["object"]

        # 构建提示
        prompt = self.prompts.get_relation_extraction_prompt(
            subject["title"], subject["content"],
            object["title"], object["content"]
        )

        try:
            # 调用模型获取JSON响应
            result = await self.client.extract_json(prompt)

            if not result or "relations" not in result:
                return []

            relations = result["relations"]

            # 格式化关系
            formatted_relations = []
            for relation in relations:
                if not relation.get("predicate"):
                    continue

                # 双向关系处理
                directions = [{"subject_id": subject["id"], "object_id": object["id"]}]
                if relation.get("bidirectional"):
                    directions.append({"subject_id": object["id"], "object_id": subject["id"]})

                for direction in directions:
                    formatted_relation = {
                        "subject_id": direction["subject_id"],
                        "predicate": relation["predicate"],
                        "object_id": direction["object_id"],
                        "relation_type": relation.get("relation_type", "generic"),
                        "bidirectional": relation.get("bidirectional", False),
                        "confidence": relation.get("confidence", 0.7),
                        "context": relation.get("context", "")
                    }

                    formatted_relations.append(formatted_relation)

            return formatted_relations
        except Exception as e:
            logger.error(f"提取关系时出错: {str(e)}")
            return []

    def _post_process(self, relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """后处理：去重、格式规范化"""
        if not relations:
            return []

        # 关系去重
        unique_relations = []
        relation_keys = set()

        for relation in relations:
            key = (relation["subject_id"], relation["predicate"], relation["object_id"])
            if key not in relation_keys:
                relation_keys.add(key)

                # 标准化信息
                if "relation_type" not in relation or not relation["relation_type"]:
                    relation["relation_type"] = self._infer_relation_type(relation["predicate"])

                if "confidence" not in relation:
                    relation["confidence"] = 0.7

                unique_relations.append(relation)

        return unique_relations

    def _infer_relation_type(self, predicate: str) -> str:
        """根据谓词推断关系类型"""
        predicate_lower = predicate.lower()

        # 常见关系类型映射
        type_mappings = {
            "is_a": ["是", "是一种", "属于", "分类为", "被归类为", "is a", "is an", "type of", "kind of",
                     "subclass of"],
            "part_of": ["包含", "包括", "由组成", "是组成部分", "contains", "part of", "composed of", "consists of"],
            "has_property": ["具有", "特征是", "特点是", "性质是", "has property", "has attribute", "has feature"],
            "causes": ["导致", "引起", "造成", "刺激", "causes", "results in", "leads to", "triggers"],
            "precedes": ["先于", "在之前", "早于", "follows", "precedes", "before", "after"],
            "similar_to": ["类似于", "相似于", "好像", "如同", "similar to", "like", "resembles"],
            "located_in": ["位于", "在内", "found in", "located in", "situated in"],
            "used_for": ["用于", "用来", "作用是", "目的是", "used for", "purpose is", "used to"]
        }

        for relation_type, keywords in type_mappings.items():
            for keyword in keywords:
                if keyword in predicate_lower:
                    return relation_type

        # 默认关系类型
        return "generic"