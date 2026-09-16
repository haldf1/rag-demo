"""嵌入后端：离线哈希嵌入（零依赖）、云 API、本地 sentence-transformers。"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from typing import Protocol

import numpy as np

from .tokenizer import tokenize


class EmbeddingBackend(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray:
        ...


class HashEmbedding:
    """确定性哈希嵌入，离线可用，适合演示与快速验证。"""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    def _grams(self, text: str) -> list[str]:
        tokens = tokenize(text)
        grams = list(tokens)
        if len(tokens) > 1:
            grams.extend("".join(tokens[i : i + 2]) for i in range(len(tokens) - 1))
        return grams

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            vector = np.zeros(self.dim, dtype=np.float32)
            for gram in self._grams(text):
                digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
                index = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[index] += sign
            norm = float(np.linalg.norm(vector))
            vectors.append(vector / norm if norm > 0 else vector)
        return np.asarray(vectors, dtype=np.float32)


class CloudEmbedding:
    """通过 OpenAI 兼容的 /embeddings 接口调用云嵌入，无需 openai 包。"""

    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self.endpoint = base_url.rstrip("/") + "/embeddings"
        self.api_key = api_key
        self.model = model if not model.startswith("BAAI/") else "text-embedding-3-small"

    def embed(self, texts: list[str]) -> np.ndarray:
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"嵌入接口调用失败: HTTP {exc.code} {exc.reason}") from exc
        return np.asarray(
            [item["embedding"] for item in data["data"]], dtype=np.float32
        )


class LocalSentenceTransformer:
    """可选本地模型后端，需自行安装 sentence-transformers。"""

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "本地嵌入需要 sentence-transformers，请执行："
                "python -m pip install sentence-transformers"
            ) from exc
        resolved = (
            model_name
            if not model_name.startswith("text-embedding")
            else "BAAI/bge-m3"
        )
        self.model = SentenceTransformer(
            resolved, model_kwargs={"use_safetensors": False}
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return np.asarray(vectors, dtype=np.float32)


def _has_sentence_transformers() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except ImportError:
        return False


def get_embedding_backend(
    config, force: str | None = None
) -> tuple[EmbeddingBackend, str]:
    name = (force or config.embedding_backend or "auto").lower()
    if name == "auto":
        if config.embedding_api_key:
            name = "cloud"
        elif _has_sentence_transformers():
            name = "local"
        else:
            name = "hash"
    if name == "hash":
        return HashEmbedding(), name
    if name == "cloud":
        if not config.embedding_api_key:
            raise RuntimeError("云嵌入需要配置 RAG_EMBEDDING_API_KEY")
        return (
            CloudEmbedding(config.embedding_base_url, config.embedding_api_key, config.embedding_model),
            name,
        )
    if name == "local":
        return LocalSentenceTransformer(config.embedding_model), name
    raise ValueError(f"未知嵌入后端: {name}")
