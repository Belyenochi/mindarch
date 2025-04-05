# ai/extraction/unit_extractor.py
from typing import Dict, List, Any, Optional
import re
import asyncio
from bson import ObjectId

from loguru import logger
from ai.client import OpenAIClient
from ai.prompts.unit_prompts import UnitPrompts
from ai.evaluation.confidence import ConfidenceEvaluator


class KnowledgeUnitExtractor:
    """知识单元提取器，从文本中提取结构化知识单元"""

    def __init__(self, model: Optional[str] = None):
        """初始化提取器"""
        self.client = OpenAIClient(model)
        self.prompts = UnitPrompts()
        self.confidence_evaluator = ConfidenceEvaluator()
        self.batch_size = 5  # 批处理大小

    async def extract_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取知识单元"""
        # 将长文本分段
        chunks = self._split_text(text)

        # 批量处理
        all_units = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_results = await asyncio.gather(*[
                self._process_chunk(chunk, i + idx)
                for idx, chunk in enumerate(batch)
            ])

            for units in batch_results:
                all_units.extend(units)

        # 后处理：去重、合并、评估置信度
        processed_units = await self._post_process(all_units)

        return processed_units

    async def process_units(self, raw_units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理和增强已有的知识单元"""
        enhanced_units = []

        # 批量处理
        for i in range(0, len(raw_units), self.batch_size):
            batch = raw_units[i:i + self.batch_size]
            batch_results = await asyncio.gather(*[
                self._enhance_unit(unit) for unit in batch
            ])

            enhanced_units.extend(batch_results)

        return enhanced_units

    async def _process_chunk(self, text: str, chunk_index: int) -> List[Dict[str, Any]]:
        """处理文本块并提取知识单元"""
        # 构建提示
        prompt = self.prompts.get_extraction_prompt(text)

        try:
            # 调用模型获取JSON响应
            result = await self.client.extract_json(prompt)

            if not result or "units" not in result:
                logger.warning(f"从文本块 {chunk_index} 提取失败，未返回有效结果")
                return []

            units = result["units"]

            # 添加位置信息
            for unit in units:
                if "source" not in unit:
                    unit["source"] = {}
                unit["source"]["position"] = chunk_index

                # 确保有必要的字段
                unit["unit_type"] = unit.get("unit_type", "note")
                if "tags" not in unit:
                    unit["tags"] = []

            return units
        except Exception as e:
            logger.error(f"处理文本块 {chunk_index} 时出错: {str(e)}")
            return []

    async def _enhance_unit(self, unit: Dict[str, Any]) -> Dict[str, Any]:
        """增强知识单元，添加更多结构化信息"""
        # 复制输入单元，避免修改原始数据
        enhanced = unit.copy()

        # 如果内容不足，直接返回原始单元
        if not enhanced.get("content") or len(enhanced["content"]) < 50:
            return enhanced

        # 构建提示
        prompt = self.prompts.get_enhancement_prompt(
            enhanced.get("title", ""),
            enhanced.get("content", ""),
            enhanced.get("tags", [])
        )

        try:
            # 调用模型获取增强信息
            result = await self.client.extract_json(prompt)

            if not result:
                return enhanced

            # 更新字段，保留原始数据
            if "canonical_name" not in enhanced and "canonical_name" in result:
                enhanced["canonical_name"] = result["canonical_name"]

            if "aliases" not in enhanced and "aliases" in result:
                enhanced["aliases"] = result["aliases"]

            if "tags" in result and result["tags"]:
                # 合并并去重标签
                existing_tags = set(enhanced.get("tags", []))
                existing_tags.update(result["tags"])
                enhanced["tags"] = list(existing_tags)

            # 添加知识属性
            if "knowledge" not in enhanced:
                enhanced["knowledge"] = {}

            knowledge_fields = ["domain", "entity_type", "importance", "abstraction_level"]
            for field in knowledge_fields:
                if field in result and field not in enhanced["knowledge"]:
                    enhanced["knowledge"][field] = result[field]

            if "properties" in result:
                if "properties" not in enhanced["knowledge"]:
                    enhanced["knowledge"]["properties"] = {}
                enhanced["knowledge"]["properties"].update(result["properties"])

            # 评估置信度
            confidence = await self.confidence_evaluator.evaluate_unit(enhanced)

            if "metrics" not in enhanced:
                enhanced["metrics"] = {}
            enhanced["metrics"]["confidence"] = confidence
            enhanced["metrics"]["completeness"] = result.get("completeness", 0.7)

            return enhanced
        except Exception as e:
            logger.error(f"增强知识单元时出错: {str(e)}")
            return enhanced

    async def _post_process(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """后处理：去重、合并、格式规范化"""
        if not units:
            return []

        # 去重（基于标题相似度）
        unique_units = self._deduplicate_units(units)

        # 规范化字段
        normalized_units = []
        for unit in unique_units:
            # 确保所有必要字段存在
            if "canonical_name" not in unit or not unit["canonical_name"]:
                unit["canonical_name"] = self._generate_canonical_name(unit.get("title", ""))

            if "unit_type" not in unit:
                unit["unit_type"] = "note"

            # 截断过长的标题
            if "title" in unit and unit["title"] and len(unit["title"]) > 100:
                unit["title"] = unit["title"][:97] + "..."

            # 确保嵌套字段
            for field in ["source", "status", "knowledge", "metrics"]:
                if field not in unit:
                    unit[field] = {}

            normalized_units.append(unit)

        return normalized_units

    def _split_text(self, text: str, max_chunk_size: int = 4000) -> List[str]:
        """将文本分割为较小的块"""
        if len(text) <= max_chunk_size:
            return [text]

        # 尝试按段落分割
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = ""

        for para in paragraphs:
            # 如果段落本身超过最大大小，进一步分割
            if len(para) > max_chunk_size:
                # 先添加当前积累的内容
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # 按句子分割大段落
                sentences = re.split(r'(?<=[.!?。！？])\s+', para)

                temp_chunk = ""
                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) <= max_chunk_size:
                        temp_chunk += sentence + " "
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())

                        # 如果单个句子超过最大大小，直接按大小切割
                        if len(sentence) > max_chunk_size:
                            for i in range(0, len(sentence), max_chunk_size):
                                chunks.append(sentence[i:i + max_chunk_size])
                        else:
                            temp_chunk = sentence + " "

                if temp_chunk:
                    chunks.append(temp_chunk.strip())

            # 正常大小的段落
            elif len(current_chunk) + len(para) + 2 <= max_chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
            else:
                chunks.append(current_chunk)
                current_chunk = para

        # 添加最后剩余的内容
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _deduplicate_units(self, units: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去除重复的知识单元"""
        # 基于标题相似度检测重复
        unique_units = []
        title_map = {}  # 标题 -> 索引映射

        for unit in units:
            title = unit.get("title", "").lower()

            # 如果没有标题，直接添加
            if not title:
                unique_units.append(unit)
                continue

            # 检查是否已存在相似标题
            found_similar = False
            for existing_title in title_map:
                # 简单的相似度检查：标题包含关系或编辑距离
                if title in existing_title or existing_title in title or self._similar_titles(title, existing_title):
                    # 标记为重复
                    unit_idx = title_map[existing_title]
                    if "status" not in unique_units[unit_idx]:
                        unique_units[unit_idx]["status"] = {}

                    if "is_duplicate" not in unique_units[unit_idx]["status"]:
                        unique_units[unit_idx]["status"]["is_duplicate"] = False

                    # 如果新单元内容更长，用它替换旧单元
                    if len(unit.get("content", "")) > len(unique_units[unit_idx].get("content", "")):
                        # 保留原单元ID和部分元数据
                        if "_id" in unique_units[unit_idx]:
                            unit["_id"] = unique_units[unit_idx]["_id"]
                        unique_units[unit_idx] = unit

                    found_similar = True
                    break

            if not found_similar:
                title_map[title] = len(unique_units)
                unique_units.append(unit)

        return unique_units

    def _similar_titles(self, title1: str, title2: str, threshold: float = 0.8) -> bool:
        """检查两个标题是否相似（简化版）"""
        # 对于MVP简单实现，仅检查重叠字符比例
        shorter = title1 if len(title1) <= len(title2) else title2
        longer = title2 if len(title1) <= len(title2) else title1

        if not shorter:
            return False

        # 计算共同字符占较短标题的百分比
        common_chars = sum(1 for c in shorter if c in longer)
        similarity = common_chars / len(shorter)

        return similarity >= threshold

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
                    import time
                    name = f"unit_{int(time.time())}"

        # 长度限制
        if len(name) > 50:
            name = name[:50]

        # 确保不为空
        if not name:
            import time
            name = f"unit_{int(time.time())}"

        return name