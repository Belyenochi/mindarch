# ai/evaluation/quality.py
from typing import Dict, Any, List, Optional


class QualityEvaluator:
    """评估知识图谱整体质量"""

    async def evaluate_graph(self, units: List[Dict[str, Any]],
                             relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """评估知识图谱的整体质量"""
        # 这是一个简化版实现，实际系统可能需要更复杂的评估逻辑

        # 计算基本指标
        unit_count = len(units)
        relation_count = len(relations)

        # 知识单元平均质量
        unit_confidence = sum(unit.get("metrics", {}).get("confidence", 0.7) for unit in units) / max(1, unit_count)
        unit_completeness = sum(unit.get("metrics", {}).get("completeness", 0.7) for unit in units) / max(1, unit_count)

        # 关系平均质量
        relation_confidence = sum(relation.get("confidence", 0.7) for relation in relations) / max(1, relation_count)

        # 连通性指标 (每个单元的平均关系数)
        connectivity = relation_count / max(1, unit_count)

        # 领域覆盖度 (不同领域的数量)
        domains = set()
        for unit in units:
            domain = unit.get("knowledge", {}).get("domain", "")
            if domain:
                domains.add(domain)
        domain_coverage = len(domains)

        # 计算总体质量评分 (0-100)
        quality_score = (
                unit_confidence * 20 +  # 最高20分
                unit_completeness * 20 +  # 最高20分
                relation_confidence * 20 +  # 最高20分
                min(connectivity, 5) / 5 * 20 +  # 最高20分 (5个或更多关系获得满分)
                min(domain_coverage, 5) / 5 * 20  # 最高20分 (5个或更多领域获得满分)
        )

        return {
            "quality_score": round(quality_score, 2),
            "unit_count": unit_count,
            "relation_count": relation_count,
            "unit_confidence": round(unit_confidence, 2),
            "unit_completeness": round(unit_completeness, 2),
            "relation_confidence": round(relation_confidence, 2),
            "connectivity": round(connectivity, 2),
            "domain_coverage": domain_coverage,
            "domains": list(domains)
        }

    async def get_improvement_suggestions(self, evaluation: Dict[str, Any]) -> List[str]:
        """根据评估结果提供改进建议"""
        suggestions = []

        # 根据评估结果提供具体建议
        score = evaluation.get("quality_score", 0)

        if score < 60:
            suggestions.append("整体图谱质量较低，建议增加更多高质量知识单元和关系")

        if evaluation.get("unit_confidence", 0) < 0.7:
            suggestions.append("知识单元可信度较低，建议改进内容质量和完整性")

        if evaluation.get("relation_confidence", 0) < 0.7:
            suggestions.append("关系可信度较低，建议添加更多上下文支持和明确的关系描述")

        if evaluation.get("connectivity", 0) < 2:
            suggestions.append("图谱连通性不足，建议增加更多单元间关系")

        if evaluation.get("domain_coverage", 0) < 3:
            suggestions.append("领域覆盖度有限，建议扩展到更多相关领域")

        # 如果评分较高，也给出积极反馈
        if score > 80:
            suggestions.append("图谱整体质量良好，可以考虑进一步扩展和细化")

        return suggestions