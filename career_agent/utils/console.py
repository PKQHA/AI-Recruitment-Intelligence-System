"""
终端交互工具。

本文件负责：
1. 从终端读取多行文本输入；
2. 支持从文件路径直接读取文本；
3. 将分析结果以较友好的方式打印到控制台。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from models.analysis_models import AnalysisReport


class ConsoleIO:
    """
    终端输入输出工具类。

    把终端交互单独抽出来后，主流程会更清晰，
    后续如果切换成 Web 接口，也可以只替换这一层。
    """

    def get_text_input(self, title: str, file_path: Optional[str] = None) -> str:
        """
        获取文本输入。

        优先级如下：
        1. 如果传入文件路径，则直接读取文件；
        2. 否则，提示用户在终端中粘贴文本，并以 `END` 结束输入。

        参数：
            title: 文本标题，例如“岗位 JD”。
            file_path: 可选的文件路径。

        返回：
            str: 最终读取到的完整文本内容。
        """
        if file_path:
            return self._read_text_file(file_path)

        print(f"\n请输入{title}内容，输入 `END` 单独一行结束：")
        lines: list[str] = []
        while True:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)

        content = "\n".join(lines).strip()
        if not content:
            raise ValueError(f"{title} 不能为空。")
        return content

    def display_report(self, report: AnalysisReport) -> None:
        """
        在终端打印最终分析结果。

        参数：
            report: 招聘分析报告对象。
        """
        print("\n" + "=" * 70)
        print("AI 招聘分析结果")
        print("=" * 70)
        print(f"JD 技能关键词：{self._format_list(report.jd_result.skills)}")
        print(f"简历技能关键词：{self._format_list(report.resume_result.skills)}")
        print(f"技能匹配率：{report.match_result.match_rate_text}")
        print(f"匹配技能：{self._format_list(report.match_result.matched_skills)}")
        print(f"缺失技能：{self._format_list(report.match_result.missing_skills)}")
        print(f"简历额外技能：{self._format_list(report.match_result.extra_resume_skills)}")
        print("学习建议：")

        for index, suggestion in enumerate(report.learning_suggestions, start=1):
            print(f"{index}. {suggestion}")

        print("=" * 70 + "\n")

    def _read_text_file(self, file_path: str) -> str:
        """
        读取文本文件。

        参数：
            file_path: 文本文件路径。

        返回：
            str: 文件内容。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"未找到文件：{path}")

        content = path.read_text(encoding="utf-8").strip()
        if not content:
            raise ValueError(f"文件内容为空：{path}")
        return content

    def _format_list(self, items: list[str]) -> str:
        """
        将列表格式化为适合终端展示的字符串。

        参数：
            items: 待展示列表。

        返回：
            str: 格式化后的字符串。
        """
        return "、".join(items) if items else "无"
