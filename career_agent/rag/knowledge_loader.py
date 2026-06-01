"""
技能知识库加载器。

V2 的知识库以 Markdown 文件形式维护，方便人工持续补充。
本模块负责读取 Markdown，并按二级标题切分成适合向量检索的知识片段。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class RawKnowledgeChunk:
    """
    原始知识片段。

    title 用于展示和 metadata，content 用于向量化与 RAG 上下文。
    """

    title: str
    content: str


class KnowledgeLoader:
    """
    技能知识库 Markdown 加载器。
    """

    def __init__(self, knowledge_file: Path | None = None) -> None:
        """
        初始化加载器。

        参数：
            knowledge_file: 可选知识库文件路径，默认使用项目内置知识库。
        """
        self._knowledge_file = knowledge_file or (
            Path(__file__).resolve().parent.parent / "data" / "skill_knowledge.md"
        )

    def load_chunks(self) -> List[RawKnowledgeChunk]:
        """
        读取并切分知识库。

        返回：
            List[RawKnowledgeChunk]: 可被 FAISS 建库的知识片段列表。
        """
        if not self._knowledge_file.exists():
            raise FileNotFoundError(f"未找到技能知识库文件：{self._knowledge_file}")

        content = self._knowledge_file.read_text(encoding="utf-8")
        return self._split_markdown(content)

    def _split_markdown(self, content: str) -> List[RawKnowledgeChunk]:
        """
        根据 Markdown 二级标题切分文本。

        参数：
            content: Markdown 原文。

        返回：
            List[RawKnowledgeChunk]: 切分后的知识片段。
        """
        chunks: List[RawKnowledgeChunk] = []
        current_title = "通用技能建议"
        current_lines: list[str] = []

        for line in content.splitlines():
            if line.startswith("## "):
                self._append_chunk(chunks, current_title, current_lines)
                current_title = line.replace("## ", "", 1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        self._append_chunk(chunks, current_title, current_lines)
        return chunks

    def _append_chunk(
        self,
        chunks: List[RawKnowledgeChunk],
        title: str,
        lines: list[str],
    ) -> None:
        """
        将当前累计内容追加到结果中。
        """
        body = "\n".join(lines).strip()
        if body:
            chunks.append(RawKnowledgeChunk(title=title, content=body))
