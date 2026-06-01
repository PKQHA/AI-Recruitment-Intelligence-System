"""
OpenAI-compatible client wrapper.

The project can use OpenAI directly or Qwen through an OpenAI-compatible
base_url. Embedding calls are always batched to keep each request within
providers that limit input arrays to at most 10 contents.
"""

from __future__ import annotations

from typing import Any, List

from core.settings import Settings


EMBEDDING_BATCH_SIZE = 10


class OpenAIClientWrapper:
    """Small wrapper around the OpenAI-compatible SDK."""

    def __init__(self, settings: Settings) -> None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as error:
            raise ModuleNotFoundError(
                "未安装 OpenAI SDK，请先执行：pip install -r requirements.txt"
            ) from error

        client_kwargs: dict[str, Any] = {"api_key": settings.api_key}
        if settings.base_url:
            client_kwargs["base_url"] = settings.base_url

        self._settings = settings
        self._client = OpenAI(**client_kwargs)

    def chat(
        self,
        messages: List[dict[str, str]],
        temperature: float = 0.2,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Call the chat completion API and return text content."""
        try:
            request_kwargs: dict[str, Any] = {
                "model": self._settings.model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                request_kwargs["response_format"] = response_format

            response = self._client.chat.completions.create(
                **request_kwargs,
            )
            content = response.choices[0].message.content
            return content.strip() if content else ""
        except Exception as error:  # noqa: BLE001
            raise RuntimeError(f"调用大模型接口失败：{error}") from error

    def supports_json_schema_response_format(self) -> bool:
        """Return whether the configured provider likely supports json_schema."""
        model = self._settings.model.lower()
        base_url = self._settings.base_url.lower()
        if "qwen" in model or "dashscope" in base_url or "aliyun" in base_url:
            return False
        if model.startswith(("gpt-3.5", "gpt-4-turbo", "gpt-4-vision")):
            return False
        return model.startswith(("gpt-4.1", "gpt-4o", "gpt-5", "o1", "o3", "o4"))

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed any number of text contents using safe batches.

        No caller needs to know the provider limit. This method guarantees that
        each embeddings request contains at most 10 input strings, then merges
        all returned vectors in the original order.
        """
        cleaned_texts = [text for text in texts if text]
        if not cleaned_texts:
            return []

        try:
            embeddings: List[List[float]] = []
            for start in range(0, len(cleaned_texts), EMBEDDING_BATCH_SIZE):
                batch = cleaned_texts[start : start + EMBEDDING_BATCH_SIZE]
                response = self._client.embeddings.create(
                    model=self._settings.embedding_model,
                    input=batch,
                )
                embeddings.extend(item.embedding for item in response.data)
            return embeddings
        except Exception as error:  # noqa: BLE001
            raise RuntimeError(f"调用向量模型失败：{error}") from error
