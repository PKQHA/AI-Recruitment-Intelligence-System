"""
兼容旧版配置入口。

当前项目已经升级为模块化结构，推荐直接使用 `core.settings.Settings`。
保留本文件的目的，是避免旧代码在导入 `config.py` 时立即报错。
"""

from core.settings import Settings

__all__ = ["Settings"]
