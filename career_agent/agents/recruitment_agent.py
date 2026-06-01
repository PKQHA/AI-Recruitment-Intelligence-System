"""
招聘分析 Agent。

这个 Agent 是系统中的核心编排器，负责把多个独立服务连接起来：
1. 提取 JD 技能
2. 提取简历技能
3. 计算匹配率
4. 生成学习建议

通过这种设计，我们可以让业务流程清晰可控，后续也方便替换某个服务实现。
"""

from __future__ import annotations

from models.analysis_models import AnalysisReport
from services.learning_advisor import LearningAdvisor
from services.matcher import SkillMatcher
from services.skill_extractor import SkillExtractor


class RecruitmentAnalysisAgent:
    """
    招聘分析 Agent。

    这是一个面向对象的业务总控类，对外只暴露一个 `analyze` 方法，
    让调用方可以用非常简单的方式完成整条招聘分析链路。
    """

    def __init__(
        self,
        skill_extractor: SkillExtractor,
        matcher: SkillMatcher,
        learning_advisor: LearningAdvisor,
    ) -> None:
        """
        初始化 Agent 所依赖的服务对象。

        参数：
            skill_extractor: 负责技能提取的服务。
            matcher: 负责计算技能匹配率的服务。
            learning_advisor: 负责生成学习建议的服务。
        """
        self._skill_extractor = skill_extractor
        self._matcher = matcher
        self._learning_advisor = learning_advisor

    def analyze(self, jd_text: str, resume_text: str) -> AnalysisReport:
        """
        对岗位 JD 和个人简历执行完整分析。

        参数：
            jd_text: 岗位 JD 原文。
            resume_text: 简历原文。

        返回：
            AnalysisReport: 包含技能提取结果、匹配结果和学习建议的完整报告对象。
        """
        jd_result = self._skill_extractor.extract_from_jd(jd_text)
        resume_result = self._skill_extractor.extract_from_resume(resume_text)
        match_result = self._matcher.calculate_match(
            jd_skills=jd_result.skills,
            resume_skills=resume_result.skills,
        )
        learning_suggestions = self._learning_advisor.generate_advice(
            matched_skills=match_result.matched_skills,
            missing_skills=match_result.missing_skills,
        )

        return AnalysisReport(
            jd_result=jd_result,
            resume_result=resume_result,
            match_result=match_result,
            learning_suggestions=learning_suggestions,
        )
