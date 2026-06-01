"""
技能匹配服务。

这个模块不依赖大模型，而是使用确定性逻辑计算匹配率。
这样做的好处是：
1. 结果稳定，不会因模型波动而变化；
2. 逻辑可解释，便于用户理解为什么匹配率是这个值；
3. 计算成本低，适合作为分析链路中的基础能力。
"""

from __future__ import annotations

from models.analysis_models import MatchResult
from utils.text import build_skill_index


class SkillMatcher:
    """
    技能匹配计算器。

    核心思路是：
    - 以 JD 技能作为目标集合
    - 以简历技能作为候选集合
    - 统计交集与差集，进而计算匹配率
    """

    def calculate_match(self, jd_skills: list[str], resume_skills: list[str]) -> MatchResult:
        """
        计算 JD 与简历之间的技能匹配结果。

        参数：
            jd_skills: 从岗位 JD 中提取出来的技能列表。
            resume_skills: 从简历中提取出来的技能列表。

        返回：
            MatchResult: 包含匹配率、匹配技能、缺失技能、额外技能的结果对象。
        """
        jd_index = build_skill_index(jd_skills)
        resume_index = build_skill_index(resume_skills)

        matched_skills: list[str] = []
        missing_skills: list[str] = []

        for normalized_skill, jd_display_skill in jd_index.items():
            if normalized_skill in resume_index:
                matched_skills.append(jd_display_skill)
            else:
                missing_skills.append(jd_display_skill)

        extra_resume_skills = [
            display_skill
            for normalized_skill, display_skill in resume_index.items()
            if normalized_skill not in jd_index
        ]

        total_target_skills = len(jd_index)
        match_rate = (
            (len(matched_skills) / total_target_skills) * 100 if total_target_skills else 0.0
        )

        return MatchResult(
            match_rate=match_rate,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            extra_resume_skills=extra_resume_skills,
        )
