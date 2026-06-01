"""
技能匹配 Tool。

该 Tool 复用 V1 的 SkillMatcher，把 JD 技能与简历技能转换成匹配报告。
"""

from __future__ import annotations

from typing import Any

from services.matcher import SkillMatcher
from tools.base_tool import BaseTool, ToolResult


class SkillMatchTool(BaseTool):
    """
    技能匹配 Tool。
    """

    name = "skill_match"
    description = "计算 JD 技能和简历技能的匹配率、匹配技能、缺失技能。"

    def __init__(self, matcher: SkillMatcher) -> None:
        """
        初始化 Tool。
        """
        self._matcher = matcher

    def run(self, **kwargs: Any) -> ToolResult:
        """
        执行技能匹配。
        """
        jd_skills = kwargs.get("jd_skills", [])
        resume_skills = kwargs.get("resume_skills", [])
        result = self._matcher.calculate_match(jd_skills, resume_skills)
        return ToolResult(data=result, message="技能匹配计算完成。")
