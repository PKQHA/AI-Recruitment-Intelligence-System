"""
招聘分析 LangGraph 工作流。

V2 将完整流程拆成 5 个节点：
1. extract_skills：提取 JD 和简历技能；
2. match_skills：调用 Tool 计算技能匹配；
3. retrieve_knowledge：调用 Tool 从 FAISS 知识库检索；
4. generate_roadmap：调用 Tool 生成学习建议和学习路线；
5. build_report：组装最终报告。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from models.v2_models import V2AnalysisReport
from services.skill_extractor import SkillExtractor
from tools.tool_registry import ToolRegistry
from workflows.state import RecruitmentWorkflowState


ProgressCallback = Callable[[str, int], None]


class RecruitmentWorkflow:
    """
    招聘分析 V2 工作流。

    该类负责构建并运行 LangGraph。
    """

    def __init__(
        self,
        skill_extractor: SkillExtractor,
        tool_registry: ToolRegistry,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        """
        初始化工作流依赖。
        """
        self._skill_extractor = skill_extractor
        self._tool_registry = tool_registry
        self._progress_callback = progress_callback
        self._graph = self._build_graph()

    def _report_progress(self, current_step: str, progress: int) -> None:
        if self._progress_callback:
            self._progress_callback(current_step, progress)

    def run(self, jd_text: str, resume_text: str) -> V2AnalysisReport:
        """
        运行 LangGraph 工作流。
        """
        result = self._graph.invoke({"jd_text": jd_text, "resume_text": resume_text})
        return result["final_report"]

    def _build_graph(self):
        """
        构建 LangGraph 状态图。

        这里采用线性图，便于 V2 先稳定跑通；后续可以增加条件边，
        例如匹配率很高时跳过知识库检索。
        """
        try:
            from langgraph.graph import END, START, StateGraph
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 LangGraph，请先执行：pip install -r requirements.txt"
            ) from error

        graph = StateGraph(RecruitmentWorkflowState)
        graph.add_node("extract_skills", self._extract_skills)
        graph.add_node("match_skills", self._match_skills)
        graph.add_node("retrieve_knowledge", self._retrieve_knowledge)
        graph.add_node("generate_roadmap", self._generate_roadmap)
        graph.add_node("build_report", self._build_report)

        graph.add_edge(START, "extract_skills")
        graph.add_edge("extract_skills", "match_skills")
        graph.add_edge("match_skills", "retrieve_knowledge")
        graph.add_edge("retrieve_knowledge", "generate_roadmap")
        graph.add_edge("generate_roadmap", "build_report")
        graph.add_edge("build_report", END)

        return graph.compile()

    def _extract_skills(
        self,
        state: RecruitmentWorkflowState,
    ) -> RecruitmentWorkflowState:
        """
        节点 1：提取 JD 与简历技能。
        """
        self._report_progress("正在解析职位描述（JD）", 20)
        self._report_progress("正在解析简历", 30)
        self._report_progress("正在提取技能", 40)
        with ThreadPoolExecutor(max_workers=2) as executor:
            jd_future = executor.submit(self._skill_extractor.extract_from_jd, state["jd_text"])
            resume_future = executor.submit(
                self._skill_extractor.extract_from_resume,
                state["resume_text"],
            )
            jd_result = jd_future.result()
            resume_result = resume_future.result()
        self._report_progress("技能提取完成", 55)
        return {"jd_result": jd_result, "resume_result": resume_result}

    def _match_skills(
        self,
        state: RecruitmentWorkflowState,
    ) -> RecruitmentWorkflowState:
        """
        节点 2：调用技能匹配 Tool。
        """
        self._report_progress("正在计算技能匹配度", 65)
        tool_result = self._tool_registry.call(
            "skill_match",
            jd_skills=state["jd_result"].skills,
            resume_skills=state["resume_result"].skills,
        )
        self._report_progress("正在生成能力差距分析", 72)
        return {"match_result": tool_result.data}

    def _retrieve_knowledge(
        self,
        state: RecruitmentWorkflowState,
    ) -> RecruitmentWorkflowState:
        """
        节点 3：调用 RAG Tool 检索技能知识。
        """
        self._report_progress("正在检索技能知识库", 78)
        tool_result = self._tool_registry.call(
            "skill_knowledge_search",
            missing_skills=state["match_result"].missing_skills,
        )
        self._report_progress("技能知识检索完成", 82)
        return {"knowledge_documents": tool_result.data}

    def _generate_roadmap(
        self,
        state: RecruitmentWorkflowState,
    ) -> RecruitmentWorkflowState:
        """
        节点 4：调用学习路线 Tool。
        """
        self._report_progress("正在生成学习路线", 88)
        tool_result = self._tool_registry.call(
            "learning_roadmap",
            matched_skills=state["match_result"].matched_skills,
            missing_skills=state["match_result"].missing_skills,
            knowledge_documents=state.get("knowledge_documents", []),
            jd_text=state.get("jd_text", ""),
            resume_text=state.get("resume_text", ""),
        )
        self._report_progress("正在生成简历优化建议", 94)
        return {
            "learning_suggestions": tool_result.data["suggestions"],
            "learning_roadmap": tool_result.data["roadmap"],
        }

    def _build_report(
        self,
        state: RecruitmentWorkflowState,
    ) -> RecruitmentWorkflowState:
        """
        节点 5：组装最终 V2 报告。
        """
        self._report_progress("正在整理分析报告", 98)
        report = V2AnalysisReport(
            jd_result=state["jd_result"],
            resume_result=state["resume_result"],
            match_result=state["match_result"],
            knowledge_documents=state.get("knowledge_documents", []),
            learning_suggestions=state.get("learning_suggestions", []),
            learning_roadmap=state.get("learning_roadmap", []),
        )
        self._report_progress("分析完成", 100)
        return {"final_report": report}
