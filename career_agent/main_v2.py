"""
AI 招聘分析 Agent V2 入口文件。

V2 在 V1 的基础上新增：
1. LangGraph 工作流编排；
2. Tool 调用机制；
3. 技能知识库 RAG；
4. FAISS 向量检索；
5. 自动生成学习路线。

本文件只负责命令行交互和对象装配，不承载复杂业务逻辑。
"""

from __future__ import annotations

import argparse

from clients.openai_client import OpenAIClientWrapper
from core.settings import Settings
from rag.skill_knowledge_base import SkillKnowledgeBase
from services.learning_advisor import LearningAdvisor
from services.matcher import SkillMatcher
from services.skill_extractor import SkillExtractor
from tools.tool_registry import build_default_tool_registry
from utils.console import ConsoleIO
from utils.console_v2 import ConsoleIOV2
from workflows.recruitment_workflow import RecruitmentWorkflow


def build_argument_parser() -> argparse.ArgumentParser:
    """
    构建 V2 命令行参数解析器。

    返回：
        argparse.ArgumentParser: 支持 JD/简历文件和 RAG 参数的解析器。
    """
    parser = argparse.ArgumentParser(
        description="AI 招聘分析 Agent V2：LangGraph + Tool + RAG + FAISS。"
    )
    parser.add_argument("--jd-file", dest="jd_file", help="岗位 JD 文本文件路径。")
    parser.add_argument("--resume-file", dest="resume_file", help="个人简历文本文件路径。")
    parser.add_argument(
        "--top-k",
        dest="top_k",
        type=int,
        default=4,
        help="每次 RAG 检索返回的知识片段数量，默认 4。",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="强制重建 FAISS 向量索引，适合知识库文件更新后使用。",
    )
    return parser


def main() -> None:
    """
    V2 程序主函数。

    流程：
    1. 加载配置；
    2. 获取 JD 和简历；
    3. 初始化 LLM、RAG 和工具注册表；
    4. 通过 LangGraph 工作流执行完整分析；
    5. 在终端打印 V2 报告。
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    base_console = ConsoleIO()
    jd_text = base_console.get_text_input("岗位 JD", args.jd_file)
    resume_text = base_console.get_text_input("个人简历", args.resume_file)

    client_wrapper = OpenAIClientWrapper(settings)
    skill_extractor = SkillExtractor(client_wrapper)
    matcher = SkillMatcher()
    learning_advisor = LearningAdvisor(client_wrapper)
    knowledge_base = SkillKnowledgeBase(
        client_wrapper=client_wrapper,
        top_k=args.top_k,
        rebuild_index=args.rebuild_index,
    )
    tool_registry = build_default_tool_registry(
        matcher=matcher,
        knowledge_base=knowledge_base,
        learning_advisor=learning_advisor,
    )

    workflow = RecruitmentWorkflow(
        skill_extractor=skill_extractor,
        tool_registry=tool_registry,
    )
    report = workflow.run(jd_text=jd_text, resume_text=resume_text)

    ConsoleIOV2().display_report(report)


if __name__ == "__main__":
    main()
