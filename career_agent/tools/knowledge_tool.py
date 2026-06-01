"""
技能知识检索 Tool。

该 Tool 调用 RAG 知识库，根据缺失技能检索学习资料、实践方向和简历表达建议。
"""

from __future__ import annotations

from typing import Any

from rag.skill_knowledge_base import SkillKnowledgeBase
from tools.base_tool import BaseTool, ToolResult


class SkillKnowledgeSearchTool(BaseTool):
    """
    技能知识库检索 Tool。
    """

    name = "skill_knowledge_search"
    description = "根据缺失技能，从 FAISS 技能知识库中检索相关知识片段。"

    def __init__(self, knowledge_base: SkillKnowledgeBase) -> None:
        """
        初始化知识检索 Tool。
        """
        self._knowledge_base = knowledge_base

    def run(self, **kwargs: Any) -> ToolResult:
        """
        执行 RAG 检索。
        """
        missing_skills = kwargs.get("missing_skills", [])
        top_k = kwargs.get("top_k")
        documents = self._knowledge_base.search_by_skills(missing_skills, top_k=top_k)
        return ToolResult(data=documents, message="技能知识库检索完成。")
