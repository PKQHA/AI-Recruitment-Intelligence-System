"""
Prompt 模板加载工具。

由于技能提取和建议生成都依赖 Prompt，
把模板独立存放并通过工具加载，可以让业务代码更加清晰，
也便于后续针对不同场景单独优化 Prompt。
"""

from __future__ import annotations

from pathlib import Path


class PromptLoader:
    """
    Prompt 模板加载器。

    该类提供统一的模板读取和变量替换能力。
    """

    PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

    @classmethod
    def load(cls, file_name: str, **kwargs: str) -> str:
        """
        读取指定 Prompt 文件并进行模板变量替换。

        参数：
            file_name: Prompt 文件名。
            **kwargs: 模板中的占位变量。

        返回：
            str: 格式化后的 Prompt 文本。
        """
        prompt_path = cls.PROMPT_DIR / file_name
        if not prompt_path.exists():
            raise FileNotFoundError(f"未找到 Prompt 文件：{prompt_path}")

        template = prompt_path.read_text(encoding="utf-8")

        # Prompt 中经常会包含 JSON 示例，直接使用 str.format 会误解析 JSON 大括号。
        # 这里采用明确的 `{变量名}` 替换方式，让模板可以自然书写 JSON。
        for key, value in kwargs.items():
            template = template.replace("{" + key + "}", value)

        return template
