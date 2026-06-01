"""
学习建议生成服务。

该服务优先调用大模型，根据“已匹配技能”和“缺失技能”生成建议；
如果模型调用失败，则回退到本地规则建议，确保程序具备基础可用性。
"""

from __future__ import annotations

import json
from typing import List

from clients.openai_client import OpenAIClientWrapper
from utils.prompt_loader import PromptLoader
from utils.text import unique_preserve_order


class LearningAdvisor:
    """
    学习建议生成器。

    这个类的职责非常单一：根据技能差距给出后续学习方向。
    这种单一职责设计有助于未来独立优化建议策略。
    """

    def __init__(self, client_wrapper: OpenAIClientWrapper) -> None:
        """
        初始化建议生成服务。

        参数：
            client_wrapper: 已封装好的 OpenAI 客户端。
        """
        self._client_wrapper = client_wrapper

    def generate_advice(
        self, matched_skills: List[str], missing_skills: List[str]
    ) -> List[str]:
        """
        生成学习建议。

        参数：
            matched_skills: 已匹配到的技能列表。
            missing_skills: 当前缺失的技能列表。

        返回：
            List[str]: 建议文本列表。
        """
        if not missing_skills:
            return [
                "整体技能覆盖度较高，建议继续打磨与岗位最相关的项目深度，并准备可量化的成果描述。",
                "把已匹配技能整理成 2 到 3 个代表性项目案例，面试时用 STAR 方法说明你的贡献和结果。",
                "进一步补充业务理解与工程落地细节，例如性能优化、异常处理、评估指标设计等内容。",
            ]

        prompt = PromptLoader.load(
            "learning_advice_prompt.txt",
            matched_skills="、".join(matched_skills) or "暂无",
            missing_skills="、".join(missing_skills),
        )
        messages = [
            {
                "role": "system",
                "content": "你是专业的职业发展顾问，擅长把技能差距转成具体学习路径。",
            },
            {"role": "user", "content": prompt},
        ]

        response_text = ""
        try:
            response_text = self._client_wrapper.chat(
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            payload = self._parse_json_payload(response_text)
            suggestions = payload.get("suggestions", [])
            cleaned_suggestions = self._sanitize_suggestions(suggestions)
            if cleaned_suggestions:
                return cleaned_suggestions
        except Exception as error:  # noqa: BLE001
            print("Learning advice generation failed, using fallback advice.")
            print(f"LLM Raw Output: {response_text}")
            print(f"error: {error}")

        return self._build_fallback_advice(matched_skills, missing_skills)

    def _parse_json_payload(self, response_text: str) -> dict:
        """
        尝试把模型输出解析为 JSON 对象。

        参数：
            response_text: 模型返回的原始文本。

        返回：
            dict: 解析后的 JSON 对象；无法解析时返回空字典。
        """
        cleaned_text = response_text.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

        try:
            payload = json.loads(cleaned_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                "学习建议 LLM 输出不是合法 JSON。"
                f"\n原始返回内容：{response_text}"
                f"\nJSON解析错误：{error}"
            ) from error

        if not isinstance(payload, dict):
            raise ValueError(
                "学习建议 LLM 输出必须是 JSON object。"
                f"\n原始返回内容：{response_text}"
                f"\nparsed_result：{payload}"
            )
        return payload

    def _sanitize_suggestions(self, suggestions: List[str]) -> List[str]:
        """
        清洗并去重建议列表。

        参数：
            suggestions: 模型原始返回的建议列表。

        返回：
            List[str]: 可直接用于展示的建议列表。
        """
        normalized = [
            str(item).strip(" -•\t\r\n")
            for item in suggestions
            if isinstance(item, str) and item.strip()
        ]
        return unique_preserve_order(normalized)

    def _build_fallback_advice(
        self, matched_skills: List[str], missing_skills: List[str]
    ) -> List[str]:
        """
        当模型建议生成失败时，构建本地兜底建议。

        这样设计的目的是提升程序健壮性，避免模型异常导致结果页为空。
        """
        suggestions: List[str] = []

        for skill in missing_skills[:3]:
            suggestions.append(
                f"优先补齐 `{skill}`：先系统学习核心概念，再做一个与岗位相关的小项目，把成果写进简历。"
            )

        suggestions.append(
            "围绕缺失技能整理学习计划，建议按照“基础概念 -> 小型实战 -> 项目复盘 -> 简历量化表达”的顺序推进。"
        )

        if matched_skills:
            suggestions.append(
                f"继续强化你已经具备的 `{matched_skills[0]}` 等优势技能，准备能证明业务价值或工程能力的案例。"
            )

        return unique_preserve_order(suggestions)
