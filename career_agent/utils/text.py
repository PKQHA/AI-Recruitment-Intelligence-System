"""
文本与技能标准化工具。

技能匹配并不只是简单字符串比较。
例如：
- Python 3 应视为 Python
- NLP 可以视为 自然语言处理
- Machine Learning 可以视为 机器学习

因此，我们在这里提供轻量的标准化函数，提升匹配结果的稳定性。
"""

from __future__ import annotations

import re


SKILL_ALIAS_MAP = {
    "python 3": "python",
    "py": "python",
    "natural language processing": "自然语言处理",
    "nlp": "自然语言处理",
    "machine learning": "机器学习",
    "ml": "机器学习",
    "deep learning": "深度学习",
    "large language model": "llm",
    "large language models": "llm",
    "llm application development": "llm 应用开发",
}


def normalize_skill_name(skill: str) -> str:
    """
    标准化技能名称。

    参数：
        skill: 原始技能文本。

    返回：
        str: 标准化后的技能文本，可用于匹配比较。
    """
    cleaned = skill.strip().lower()
    cleaned = cleaned.replace("（", "(").replace("）", ")")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^[\-•\d\.\)\s]+", "", cleaned)
    cleaned = SKILL_ALIAS_MAP.get(cleaned, cleaned)
    return cleaned


def unique_preserve_order(items: list[str]) -> list[str]:
    """
    对列表进行去重，同时保留原始顺序。

    参数：
        items: 原始列表。

    返回：
        list[str]: 去重后的列表。
    """
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        marker = item.strip()
        if not marker or marker in seen:
            continue
        seen.add(marker)
        result.append(marker)

    return result


def build_skill_index(skills: list[str]) -> dict[str, str]:
    """
    将技能列表转换为“标准化技能 -> 展示技能”的索引字典。

    这样做的目的是：
    - 比较时使用标准化结果
    - 展示时保留更友好的原始表达

    参数：
        skills: 原始技能列表。

    返回：
        dict[str, str]: 技能索引字典。
    """
    index: dict[str, str] = {}

    for skill in skills:
        cleaned_skill = skill.strip()
        if not cleaned_skill:
            continue

        normalized_skill = normalize_skill_name(cleaned_skill)
        if normalized_skill not in index:
            index[normalized_skill] = cleaned_skill

    return index
