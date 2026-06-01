"""
Tool 注册表。

工作流通过注册表按名称调用 Tool，从而实现“节点编排”和“具体工具实现”的解耦。
"""

from __future__ import annotations

from typing import Any, Dict

from rag.skill_knowledge_base import SkillKnowledgeBase
from services.learning_advisor import LearningAdvisor
from services.matcher import SkillMatcher
from tools.base_tool import BaseTool, ToolResult
from tools.knowledge_tool import SkillKnowledgeSearchTool
from tools.match_tool import SkillMatchTool
from tools.roadmap_tool import LearningRoadmapTool


class ToolRegistry:
    """
    Tool 注册与调用中心。
    """

    def __init__(self) -> None:
        """
        初始化空注册表。
        """
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        注册一个 Tool。
        """
        self._tools[tool.name] = tool

    def call(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """
        按名称调用 Tool。
        """
        if tool_name not in self._tools:
            raise KeyError(f"未注册 Tool：{tool_name}")
        return self._tools[tool_name].run(**kwargs)

    def list_tools(self) -> list[str]:
        """
        返回当前已注册 Tool 名称。
        """
        return list(self._tools.keys())


def build_default_tool_registry(
    matcher: SkillMatcher,
    knowledge_base: SkillKnowledgeBase,
    learning_advisor: LearningAdvisor,
) -> ToolRegistry:
    """
    构建 V2 默认 Tool 注册表。
    """
    registry = ToolRegistry()
    registry.register(SkillMatchTool(matcher))
    registry.register(SkillKnowledgeSearchTool(knowledge_base))
    registry.register(LearningRoadmapTool(learning_advisor))
    return registry
