"""
V2 Agent facade.

This module is the single programmatic entry point for callers outside the
CLI layer. It reuses the existing V2 workflow, tools, and RAG components, then
normalizes the workflow report into a Web/API friendly dictionary.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from functools import lru_cache
from typing import Any, Callable

from clients.openai_client import OpenAIClientWrapper
from core.settings import Settings
from rag.skill_knowledge_base import SkillKnowledgeBase
from services.learning_advisor import LearningAdvisor
from services.matcher import SkillMatcher
from services.skill_extractor import SkillExtractor
from tools.tool_registry import build_default_tool_registry
from utils.embedding_text import split_text_for_embedding
from workflows.recruitment_workflow import RecruitmentWorkflow


class V2Agent:
    """Facade around the existing V2 recruitment workflow."""

    def __init__(
        self,
        top_k: int = 4,
        rebuild_index: bool = False,
        progress_callback: Callable[[str, int], None] | None = None,
    ) -> None:
        settings = Settings.from_env()
        settings.validate()

        client_wrapper = OpenAIClientWrapper(settings)
        skill_extractor = SkillExtractor(client_wrapper)
        matcher = SkillMatcher()
        learning_advisor = LearningAdvisor(client_wrapper)
        knowledge_base = SkillKnowledgeBase(
            client_wrapper=client_wrapper,
            top_k=top_k,
            rebuild_index=rebuild_index,
        )
        tool_registry = build_default_tool_registry(
            matcher=matcher,
            knowledge_base=knowledge_base,
            learning_advisor=learning_advisor,
        )

        self._workflow = RecruitmentWorkflow(
            skill_extractor=skill_extractor,
            tool_registry=tool_registry,
            progress_callback=progress_callback,
        )

    def run(self, jd: str, resume: str) -> dict[str, Any]:
        """Run V2 analysis and return the public Web response shape."""
        report = self._workflow.run(
            jd_text=_preserve_full_text_with_segments(jd),
            resume_text=_preserve_full_text_with_segments(resume),
        )
        match_result = report.match_result

        return {
            "match_rate": float(match_result.match_rate),
            "matched_skills": list(match_result.matched_skills),
            "missing_skills": list(match_result.missing_skills),
            "recommendation": list(report.learning_suggestions),
            "roadmap": [_to_plain_dict(step) for step in report.learning_roadmap],
        }


@lru_cache(maxsize=1)
def get_agent() -> V2Agent:
    """Return a cached default V2 Agent instance for Web callers."""
    return V2Agent()


def run(jd: str, resume: str) -> dict[str, Any]:
    """Public module-level entry point required by the Web layer."""
    return get_agent().run(jd=jd, resume=resume)


def run_with_progress(
    jd: str,
    resume: str,
    progress_callback: Callable[[str, int], None],
) -> dict[str, Any]:
    """Run an analysis with per-request progress callbacks."""
    return V2Agent(progress_callback=progress_callback).run(jd=jd, resume=resume)


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    return {"value": value}


def _preserve_full_text_with_segments(text: str) -> str:
    """Normalize long text by segmenting and joining without truncation."""
    return "\n\n".join(split_text_for_embedding(text))
