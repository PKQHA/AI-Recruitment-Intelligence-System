"""
V2 终端输出工具。

V2 报告比 V1 更丰富，包含 RAG 知识片段和学习路线，因此单独提供展示类。
"""

from __future__ import annotations

from models.v2_models import V2AnalysisReport


class ConsoleIOV2:
    """
    V2 终端输出类。
    """

    def display_report(self, report: V2AnalysisReport) -> None:
        """
        打印 V2 分析报告。
        """
        print("\n" + "=" * 80)
        print("AI 招聘分析 Agent V2 结果")
        print("=" * 80)
        print(f"JD 技能关键词：{self._format_list(report.jd_result.skills)}")
        print(f"简历技能关键词：{self._format_list(report.resume_result.skills)}")
        print(f"技能匹配率：{report.match_result.match_rate_text}")
        print(f"匹配技能：{self._format_list(report.match_result.matched_skills)}")
        print(f"缺失技能：{self._format_list(report.match_result.missing_skills)}")
        print(f"简历额外技能：{self._format_list(report.match_result.extra_resume_skills)}")

        print("\nRAG 检索到的技能知识：")
        if report.knowledge_documents:
            for index, document in enumerate(report.knowledge_documents, start=1):
                score_text = f"，score={document.score:.4f}" if document.score is not None else ""
                print(f"{index}. {document.title}{score_text}")
                print(f"   {document.content[:180].replace(chr(10), ' ')}")
        else:
            print("无")

        print("\n学习建议：")
        for index, suggestion in enumerate(report.learning_suggestions, start=1):
            print(f"{index}. {suggestion}")

        print("\n自动学习路线：")
        for step in report.learning_roadmap:
            print(f"- {step.phase}")
            print(f"  目标技能：{step.target_skill}")
            print(f"  学习目标：{step.goal}")
            print(f"  实践任务：{step.practice_task}")
            print(f"  简历表达：{step.resume_tip}")

        print("=" * 80 + "\n")

    def _format_list(self, items: list[str]) -> str:
        """
        格式化列表文本。
        """
        return "、".join(items) if items else "无"
