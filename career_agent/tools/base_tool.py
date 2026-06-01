"""
Tool 基类与调用结果。

这里实现一个轻量 Tool 协议，便于在不绑定某个框架装饰器的情况下，
把“技能匹配、知识检索、路线生成”等动作统一注册和调用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """
    Tool 调用结果。

    data 用于承载结构化结果，message 用于记录可读说明。
    """

    data: Any
    message: str = ""


class BaseTool(ABC):
    """
    所有 V2 Tool 的抽象基类。
    """

    name: str
    description: str

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """
        执行 Tool 并返回统一结果。
        """
