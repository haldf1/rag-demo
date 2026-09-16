"""混合检索：向量余弦 + BM25，RRF 融合排序。"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .bm25 import BM25
from .embeddings import get_embedding_backend
from .tokenizer import tokenize


@dataclass
class SearchResult:
    chunk_id: str
    doc_id: str
    doc_title: str
    heading: str
    text: str
    score: float
    rank: int
    vector_score: float
    bm25_score: float


class HybridSearcher:
    def __init__(self, config, index_data: dict | None = None) -> None:
        self.config = config
        self.index = index_data
        self.chunks: list[dict] = []
        self.documents: list[dict] = []
        self.matrix: np.ndarray | None = None
        self.bm25: BM25 | None = None
        self.backend_name = "hash"
        self.embeddings = None
        if index_data is not None:
            self._prepare(index_data)

    def reload(self, index_data: dict) -> None:
        """使用现有嵌入模型重新加载索引数据。"""
        self._prepare(index_data, reuse_embeddings=True)

    def _prepare(self, index_data: dict, reuse_embeddings: bool = False) -> None:
        self.index = index_data
        self.chunks = index_data["chunks"]
        self.documents = index_data["documents"]
        self.backend_name = index_data["vectors"]["backend"]
        vector_data = index_data["vectors"]["data"]
        dim = int(index_data["vectors"].get("dim", 0))
        if vector_data:
            self.matrix = np.asarray(vector_data, dtype=np.float32)
        else:
            self.matrix = np.zeros((0, dim), dtype=np.float32)
        if self.matrix.size:
            norms = np.linalg.norm(self.matrix, axis=1, keepdims=True)
            self.matrix = self.matrix / np.maximum(norms, 1e-12)
        corpus_tokens = [tokenize(chunk["text"]) for chunk in self.chunks]
        self.bm25 = BM25(corpus_tokens)
        if not reuse_embeddings or self.embeddings is None:
            self.embeddings, _ = get_embedding_backend(
                self.config, force=self.backend_name
            )

    @property
    def stats(self) -> dict:
        return {
            "docs": len(self.documents),
            "chunks": len(self.chunks),
            "embedding_backend": self.backend_name,
            "dim": int(self.matrix.shape[1]) if self.matrix is not None else 0,
        }

    def search(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        if self.matrix is None or self.bm25 is None:
            raise RuntimeError("索引尚未加载，请先运行 build 或加载 index.json")
        if not self.chunks or self.matrix.size == 0:
            return []
        top_k = top_k or self.config.top_k
        query_vector = self.embeddings.embed([query])[0]
        vector_scores = self.matrix @ query_vector
        vector_order = np.argsort(-vector_scores)
        vector_rank = {int(index): rank for rank, index in enumerate(vector_order)}

        bm25_hits = self.bm25.search(tokenize(query), top_k=max(top_k * 3, 30))
        bm25_rank = {index: rank for rank, (index, _) in enumerate(bm25_hits)}
        bm25_score_map = {index: score for index, score in bm25_hits}

        fused: dict[int, float] = {}
        for index in range(len(self.chunks)):
            score = 0.0
            if index in vector_rank:
                score += self.config.vector_weight / (
                    self.config.rrf_k + vector_rank[index]
                )
            if index in bm25_rank:
                score += self.config.bm25_weight / (self.config.rrf_k + bm25_rank[index])
            fused[index] = score

        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)[:top_k]
        results: list[SearchResult] = []
        for rank, (index, score) in enumerate(ranked, start=1):
            chunk = self.chunks[index]
            results.append(
                SearchResult(
                    chunk_id=chunk["chunk_id"],
                    doc_id=chunk["doc_id"],
                    doc_title=chunk["doc_title"],
                    heading=chunk["heading"],
                    text=chunk["text"],
                    score=float(score),
                    rank=rank,
                    vector_score=float(vector_scores[index]),
                    bm25_score=float(bm25_score_map.get(index, 0.0)),
                )
            )
        return results
