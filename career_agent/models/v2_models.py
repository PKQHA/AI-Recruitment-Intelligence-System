"""
V2 数据模型。

V1 已经有基础分析模型，V2 新增 RAG 知识片段、学习路线步骤和工作流报告模型。
这些模型让 LangGraph 节点之间的数据传递更清晰，也让终端输出层更容易展示。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from models.analysis_models import MatchResult, SkillExtractionResult
from pydantic import BaseModel  # pyright: ignore[reportMissingImports]


class RoadmapItem(BaseModel):
    phase: str
    target_skill: str
    reason: str
    goal: str
    learning_path: List[str]
    practice_task: str
    project_idea: str
    resume_tip: str

    class Config:
        extra = "forbid"


class RoadmapResponse(BaseModel):
    roadmap: List[RoadmapItem]

    class Config:
        extra = "forbid"


class LearningPlanResponse(BaseModel):
    suggestions: List[str]
    roadmap: List[RoadmapItem]

    class Config:
        extra = "forbid"


@dataclass
class KnowledgeDocument:
    """
    技能知识库检索结果。

    每个对象代表 RAG 从 FAISS 中找到的一段技能知识。
    """

    title: str
    content: str
    score: float | None = None
    source: str = "skill_knowledge_base"


@dataclass
class LearningRoadmapStep:
    """
    学习路线中的单个步骤。

    V2 不只输出建议，还会给出阶段、目标、练习任务和简历呈现方式。
    """

    phase: str
    target_skill: str
    goal: str
    practice_task: str
    resume_tip: str
    reason: str = ""
    learning_path: List[str] = field(default_factory=list)
    project_idea: str = ""


@dataclass
class V2AnalysisReport:
    """
    V2 完整分析报告。

    该报告聚合 V1 分析结果、RAG 知识和自动学习路线。
    """

    jd_result: SkillExtractionResult
    resume_result: SkillExtractionResult
    match_result: MatchResult
    knowledge_documents: List[KnowledgeDocument] = field(default_factory=list)
    learning_suggestions: List[str] = field(default_factory=list)
    learning_roadmap: List[LearningRoadmapStep] = field(default_factory=list)
