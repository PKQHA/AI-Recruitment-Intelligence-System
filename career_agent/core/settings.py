"""
项目配置管理。

本文件负责：
1. 从 `.env` 与系统环境变量中读取配置。
2. 统一处理 OpenAI Key、模型名和 Base URL。
3. 对缺失配置进行校验，尽早在程序启动阶段暴露问题。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value

    try:
        import streamlit as st
    except ModuleNotFoundError:
        return default

    try:
        value = st.secrets.get(name, default)
    except Exception:
        return default

    return str(value)


@dataclass
class Settings:
    """
    应用配置对象。

    之所以使用 `dataclass`，是因为它非常适合承载一组结构清晰、不可随意散落的配置项。
    """

    api_key: str
    model: str
    embedding_model: str
    base_url: str = ""

    @classmethod
    def from_env(cls) -> "Settings":
        """
        从环境变量中创建配置对象。

        为了兼容你当前目录中已有的旧字段，本方法同时支持：
        - `OPENAI_API_KEY`
        - `QWEN_API_KEY`

        返回：
            Settings: 加载完成的配置实例。
        """
        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 python-dotenv，请先执行：pip install -r requirements.txt"
            ) from error

        load_dotenv()

        openai_api_key = _get_setting("OPENAI_API_KEY")
        qwen_api_key = _get_setting("QWEN_API_KEY")
        openai_base_url = _get_setting("OPENAI_BASE_URL")
        qwen_base_url = _get_setting("QWEN_BASE_URL")

        api_key = openai_api_key or qwen_api_key
        base_url = openai_base_url or qwen_base_url

        if _get_setting("OPENAI_MODEL"):
            model = _get_setting("OPENAI_MODEL")
        elif _get_setting("QWEN_MODEL"):
            model = _get_setting("QWEN_MODEL")
        elif qwen_api_key or qwen_base_url:
            model = "qwen-plus"
        else:
            model = "gpt-4.1-mini"

        if _get_setting("OPENAI_EMBEDDING_MODEL"):
            embedding_model = _get_setting("OPENAI_EMBEDDING_MODEL")
        elif _get_setting("QWEN_EMBEDDING_MODEL"):
            embedding_model = _get_setting("QWEN_EMBEDDING_MODEL")
        elif qwen_api_key or qwen_base_url:
            embedding_model = "text-embedding-v4"
        else:
            embedding_model = "text-embedding-3-small"

        return cls(
            api_key=api_key.strip(),
            model=model.strip(),
            embedding_model=embedding_model.strip(),
            base_url=base_url.strip(),
        )

    def validate(self) -> None:
        """
        校验关键配置。

        如果 API Key 缺失，程序不应该继续执行，因为后续的技能提取与建议生成
        都依赖模型能力。
        """
        if not self.api_key:
            raise ValueError(
                "未读取到 API Key。请在 `.env` 中设置 `OPENAI_API_KEY`，"
                "或者使用兼容字段 `QWEN_API_KEY`。"
            )
