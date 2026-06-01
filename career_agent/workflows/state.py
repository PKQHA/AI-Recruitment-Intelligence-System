"""
LangGraph 工作流状态定义。

所有节点通过同一个 State 传递数据。
TypedDict 可以让每个节点清楚知道自己读取和写入哪些字段。
"""

from __future__ import annotations

from typing import TypedDict

from models.analysis_models import MatchResult, SkillExtractionResult
from models.v2_models import KnowledgeDocument, LearningRoadmapStep, V2AnalysisReport


class RecruitmentWorkflowState(TypedDict, total=False):
    """
    AI 招聘分析 V2 的 LangGraph 状态。
    """

    jd_text: str
    resume_text: str
    jd_result: SkillExtractionResult
    resume_result: SkillExtractionResult
    match_result: MatchResult
    knowledge_documents: list[KnowledgeDocument]
    learning_suggestions: list[str]
    learning_roadmap: list[LearningRoadmapStep]
    final_report: V2AnalysisReport
