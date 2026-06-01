"""
技能提取服务。

本服务负责调用大模型，从岗位 JD 或简历文本中提取技能关键词。
为了让代码更清晰，我们把“JD 提取”和“简历提取”统一收口到一个类中，
通过不同的 Prompt 模板实现差异化抽取。
"""

from __future__ import annotations

import json
from typing import Any, List

from clients.openai_client import OpenAIClientWrapper
from models.analysis_models import SkillExtractionResult
from utils.prompt_loader import PromptLoader
from utils.text import unique_preserve_order


class SkillExtractor:
    """
    技能提取器。

    该类通过 OpenAI 模型把非结构化文本转成结构化技能关键词列表，
    是整个项目最关键的上游能力之一。
    """

    def __init__(self, client_wrapper: OpenAIClientWrapper) -> None:
        """
        初始化技能提取服务。

        参数：
            client_wrapper: 已封装好的 OpenAI 客户端对象。
        """
        self._client_wrapper = client_wrapper

    def extract_from_jd(self, jd_text: str) -> SkillExtractionResult:
        """
        从岗位 JD 中提取技能关键词。

        参数：
            jd_text: 岗位 JD 原始文本。

        返回：
            SkillExtractionResult: JD 技能提取结果。
        """
        skills = self._extract_skills(
            prompt_name="jd_prompt.txt",
            content=jd_text,
            source_name="岗位 JD",
        )
        return SkillExtractionResult(source_name="岗位 JD", skills=skills)

    def extract_from_resume(self, resume_text: str) -> SkillExtractionResult:
        """
        从简历文本中提取技能关键词。

        参数：
            resume_text: 简历原始文本。

        返回：
            SkillExtractionResult: 简历技能提取结果。
        """
        skills = self._extract_skills(
            prompt_name="resume_prompt.txt",
            content=resume_text,
            source_name="个人简历",
        )
        return SkillExtractionResult(source_name="个人简历", skills=skills)

    def _extract_skills(self, prompt_name: str, content: str, source_name: str) -> List[str]:
        """
        执行通用技能提取流程。

        参数：
            prompt_name: Prompt 模板文件名。
            content: 需要提取技能的原始文本。
            source_name: 当前数据来源名称，仅用于错误提示。

        返回：
            List[str]: 去重清洗后的技能列表。
        """
        prompt = PromptLoader.load(prompt_name, content=content.strip())
        messages = [
            {
                "role": "system",
                "content": "你擅长从招聘文本中抽取标准化技能关键词，并且严格遵守 JSON 输出格式。",
            },
            {"role": "user", "content": prompt},
        ]
        response_text = self._client_wrapper.chat(messages=messages, temperature=0.1)
        payload = self._parse_json_payload(response_text)
        skills = self._extract_skill_list(payload)

        if not skills:
            raise ValueError(f"{source_name} 技能提取失败：模型未返回有效技能列表。")

        return self._sanitize_skills(skills)

    def _parse_json_payload(self, response_text: str) -> dict[str, Any]:
        """
        尝试将模型输出解析为 JSON 对象。

        参数：
            response_text: 模型原始响应文本。

        返回：
            dict[str, Any]: 成功时返回 JSON 对象，失败时返回空字典。
        """
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```json", "").replace("```", "").strip()

        try:
            payload = json.loads(cleaned_text)
            return payload if isinstance(payload, dict) else {}
        except json.JSONDecodeError:
            return {}

    def _extract_skill_list(self, payload: dict[str, Any]) -> List[str]:
        """
        从 JSON 对象中提取 `skills` 字段。

        参数：
            payload: 模型返回的 JSON 对象。

        返回：
            List[str]: 技能列表；若格式不正确则返回空列表。
        """
        skills = payload.get("skills", [])
        if not isinstance(skills, list):
            return []
        return [str(skill) for skill in skills]

    def _sanitize_skills(self, skills: List[str]) -> List[str]:
        """
        对技能结果做基础清洗。

        这里会处理：
        - 空字符串
        - 多余符号
        - 重复项

        参数：
            skills: 模型原始技能结果。

        返回：
            List[str]: 清洗后的技能列表。
        """
        cleaned_skills = [
            str(skill).strip(" -•\t\r\n")
            for skill in skills
            if str(skill).strip(" -•\t\r\n")
        ]
        return unique_preserve_order(cleaned_skills)
