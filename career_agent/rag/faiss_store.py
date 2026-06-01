"""
FAISS 向量库封装。

本模块负责把技能知识库转换成向量索引，并提供相似度检索能力。
为了让项目首次运行更顺滑，索引不存在时会自动构建；知识库更新后可通过
`main_v2.py --rebuild-index` 强制重建。
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from models.v2_models import KnowledgeDocument
from rag.embedding_adapter import OpenAIEmbeddingAdapter
from rag.knowledge_loader import RawKnowledgeChunk
from utils.embedding_text import split_text_for_embedding


class FaissSkillStore:
    """
    技能知识库 FAISS 存储层。
    """

    def __init__(
        self,
        embedding_adapter: OpenAIEmbeddingAdapter,
        index_dir: Path | None = None,
    ) -> None:
        """
        初始化 FAISS 存储层。

        参数：
            embedding_adapter: 向量模型适配器。
            index_dir: FAISS 本地索引保存目录。
        """
        self._embedding_adapter = embedding_adapter
        self._index_dir = index_dir or (
            Path(__file__).resolve().parent.parent / "vector_store" / "faiss_skill_index"
        )
        self._vector_store = None

    def load_or_build(
        self,
        chunks: List[RawKnowledgeChunk],
        rebuild_index: bool = False,
    ) -> None:
        """
        加载已有索引，或根据知识库片段重新构建索引。
        """
        if self._index_exists() and not rebuild_index:
            self._vector_store = self._load_index()
            return

        self._vector_store = self._build_index(chunks)
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._vector_store.save_local(str(self._index_dir))

    def similarity_search(self, query: str, top_k: int = 4) -> List[KnowledgeDocument]:
        """
        使用 FAISS 执行相似度检索。

        参数：
            query: 检索查询文本。
            top_k: 返回片段数量。

        返回：
            List[KnowledgeDocument]: 检索到的技能知识片段。
        """
        if self._vector_store is None:
            raise RuntimeError("FAISS 索引尚未加载，请先调用 load_or_build。")

        results = self._vector_store.similarity_search_with_score(query, k=top_k)
        documents: List[KnowledgeDocument] = []

        for document, score in results:
            documents.append(
                KnowledgeDocument(
                    title=document.metadata.get("title", "未知技能知识"),
                    content=document.page_content,
                    score=float(score),
                    source=document.metadata.get("source", "skill_knowledge_base"),
                )
            )

        return documents

    def _index_exists(self) -> bool:
        """
        判断 FAISS 本地索引是否已经存在。
        """
        return (self._index_dir / "index.faiss").exists() and (
            self._index_dir / "index.pkl"
        ).exists()

    def _load_index(self):
        """
        从本地目录加载 FAISS 索引。
        """
        try:
            from langchain_community.vectorstores import FAISS
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 FAISS/LangChain 相关依赖，请执行：pip install -r requirements.txt"
            ) from error

        return FAISS.load_local(
            str(self._index_dir),
            self._embedding_adapter,
            allow_dangerous_deserialization=True,
        )

    def _build_index(self, chunks: List[RawKnowledgeChunk]):
        """
        根据技能知识片段构建新的 FAISS 索引。
        """
        try:
            from langchain_community.vectorstores import FAISS
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 FAISS/LangChain 相关依赖，请执行：pip install -r requirements.txt"
            ) from error

        texts: list[str] = []
        metadatas: list[dict[str, str]] = []

        for chunk in chunks:
            split_contents = split_text_for_embedding(chunk.content)
            for index, content in enumerate(split_contents, start=1):
                texts.append(content)
                metadatas.append(
                    {
                        "title": chunk.title,
                        "chunk_index": str(index),
                        "source": "data/skill_knowledge.md",
                    }
                )

        return FAISS.from_texts(
            texts=texts,
            embedding=self._embedding_adapter,
            metadatas=metadatas,
        )
