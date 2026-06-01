"""
招聘分析数据模型。

通过 dataclass，我们把“技能提取结果、匹配结果、完整分析报告”
定义成清晰的结构化对象，便于后续在命令行、Web API 或数据库层复用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class SkillExtractionResult:
    """
    单个文本来源的技能提取结果。

    例如，一个 JD 会提取出一组技能；一份简历也会提取出一组技能。
    """

    source_name: str
    skills: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    """
    技能匹配结果。

    这里不仅保存匹配率，还包含匹配技能、缺失技能和额外技能，
    便于后续做更细的解释与展示。
    """

    match_rate: float
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    extra_resume_skills: List[str] = field(default_factory=list)

    @property
    def match_rate_text(self) -> str:
        """
        将数值形式的匹配率转换成适合展示的百分比文本。
        """
        return f"{self.match_rate:.2f}%"


@dataclass
class AnalysisReport:
    """
    完整分析报告。

    这是最终输出给终端展示层的数据对象，
    聚合了整个分析流程中最重要的结果。
    """

    jd_result: SkillExtractionResult
    resume_result: SkillExtractionResult
    match_result: MatchResult
    learning_suggestions: List[str] = field(default_factory=list)
