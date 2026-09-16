"""CrossEncoder 精排：对 (query, chunk_text) 打分后返回 Top-N。"""
from __future__ import annotations


class Reranker:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "rerank 需要 sentence-transformers，请先安装："
                "python -m pip install sentence-transformers"
            ) from exc
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, results, top_n: int):
        if not results:
            return results
        pairs = [(query, result.text) for result in results]
        scores = self.model.predict(pairs, show_progress_bar=False)
        ranked = sorted(zip(results, scores), key=lambda item: item[1], reverse=True)
        selected = [result for result, _ in ranked[:top_n]]
        for new_rank, result in enumerate(selected, start=1):
            result.rank = new_rank
        return selected
