"""
项目入口文件。

这个文件负责完成以下事情：
1. 解析命令行参数，支持从文本文件读取 JD/简历。
2. 在未提供文件路径时，引导用户在终端中直接粘贴多行文本。
3. 初始化配置、OpenAI 客户端与招聘分析 Agent。
4. 输出最终的技能匹配分析结果。
"""

from __future__ import annotations

import argparse

from agents.recruitment_agent import RecruitmentAnalysisAgent
from clients.openai_client import OpenAIClientWrapper
from core.settings import Settings
from services.learning_advisor import LearningAdvisor
from services.matcher import SkillMatcher
from services.skill_extractor import SkillExtractor
from utils.console import ConsoleIO


def build_argument_parser() -> argparse.ArgumentParser:
    """
    构建命令行参数解析器。

    返回：
        argparse.ArgumentParser: 已配置好的参数解析器对象。
    """
    parser = argparse.ArgumentParser(
        description="AI 招聘分析 Agent V1：提取 JD/简历技能并输出匹配分析结果。"
    )
    parser.add_argument(
        "--jd-file",
        dest="jd_file",
        help="岗位 JD 文本文件路径；如果不传，则在终端中手动粘贴。",
    )
    parser.add_argument(
        "--resume-file",
        dest="resume_file",
        help="个人简历文本文件路径；如果不传，则在终端中手动粘贴。",
    )
    return parser


def main() -> None:
    """
    程序主函数。

    这里会串联整个 V1 版本的运行流程：
    读取配置 -> 采集输入 -> 调用 Agent 分析 -> 在终端打印结果。
    """
    parser = build_argument_parser()
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.validate()

    console = ConsoleIO()
    jd_text = console.get_text_input("岗位 JD", args.jd_file)
    resume_text = console.get_text_input("个人简历", args.resume_file)

    client_wrapper = OpenAIClientWrapper(settings)
    skill_extractor = SkillExtractor(client_wrapper)
    matcher = SkillMatcher()
    learning_advisor = LearningAdvisor(client_wrapper)
    agent = RecruitmentAnalysisAgent(skill_extractor, matcher, learning_advisor)

    report = agent.analyze(jd_text=jd_text, resume_text=resume_text)
    console.display_report(report)


if __name__ == "__main__":
    main()
