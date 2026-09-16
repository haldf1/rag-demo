"""自实现 BM25 检索，避免额外依赖。"""
from __future__ import annotations

import math
from collections import Counter


class BM25:
    def __init__(
        self,
        corpus_token_lists: list[list[str]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_tokens = [list(tokens) for tokens in corpus_token_lists]
        self.doc_count = len(self.corpus_tokens)
        self.doc_lengths = [len(tokens) for tokens in self.corpus_tokens]
        self.avg_length = (
            sum(self.doc_lengths) / self.doc_count if self.doc_count else 1.0
        )
        dfs: Counter[str] = Counter()
        for tokens in self.corpus_tokens:
            for token in set(tokens):
                dfs[token] += 1
        self.idf = {
            token: math.log(1 + (self.doc_count - freq + 0.5) / (freq + 0.5))
            for token, freq in dfs.items()
        }

    def score(self, query_tokens: list[str], doc_tokens: list[str]) -> float:
        length = len(doc_tokens)
        if length == 0:
            return 0.0
        term_freq = Counter(doc_tokens)
        total = 0.0
        for token in set(query_tokens):
            freq = term_freq.get(token, 0)
            if freq == 0:
                continue
            idf = self.idf.get(token, 0.0)
            denominator = freq + self.k1 * (
                1 - self.b + self.b * length / self.avg_length
            )
            total += idf * (freq * (self.k1 + 1)) / denominator
        return total

    def search(self, query_tokens: list[str], top_k: int = 20) -> list[tuple[int, float]]:
        scored = [
            (index, self.score(query_tokens, tokens))
            for index, tokens in enumerate(self.corpus_tokens)
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]
