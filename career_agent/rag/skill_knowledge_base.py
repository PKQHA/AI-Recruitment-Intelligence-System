"""
技能知识库服务。

该服务对上层隐藏 Markdown 加载、Embedding、FAISS 索引构建和检索细节。
工作流节点只需要调用 `search_by_skills` 即可获得 RAG 上下文。
"""

from __future__ import annotations

from typing import List

from clients.openai_client import OpenAIClientWrapper
from models.v2_models import KnowledgeDocument
from rag.embedding_adapter import OpenAIEmbeddingAdapter
from rag.faiss_store import FaissSkillStore
from rag.knowledge_loader import KnowledgeLoader


class SkillKnowledgeBase:
    """
    技能知识库 RAG 服务。
    """

    def __init__(
        self,
        client_wrapper: OpenAIClientWrapper,
        top_k: int = 4,
        rebuild_index: bool = False,
    ) -> None:
        """
        初始化技能知识库。

        参数：
            client_wrapper: OpenAI 客户端封装。
            top_k: 默认检索返回数量。
            rebuild_index: 是否强制重建 FAISS 索引。
        """
        self._top_k = top_k
        self._loader = KnowledgeLoader()
        self._store = FaissSkillStore(OpenAIEmbeddingAdapter(client_wrapper))
        chunks = self._loader.load_chunks()
        self._store.load_or_build(chunks=chunks, rebuild_index=rebuild_index)

    def search_by_skills(
        self,
        skills: List[str],
        top_k: int | None = None,
    ) -> List[KnowledgeDocument]:
        """
        根据缺失技能检索相关知识。

        参数：
            skills: 缺失技能列表。
            top_k: 可选返回数量。

        返回：
            List[KnowledgeDocument]: RAG 检索结果。
        """
        if not skills:
            return []

        query = "、".join(skills)
        return self._store.similarity_search(query=query, top_k=top_k or self._top_k)
