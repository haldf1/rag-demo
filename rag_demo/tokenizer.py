"""轻量中英混合分词：英文按词，中文按字符二元组。"""
from __future__ import annotations

import math
import re

_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _WORD_RE.finditer(text):
        tokens.append(match.group(0).lower())
    for match in _CJK_RE.finditer(text):
        block = match.group(0)
        if len(block) == 1:
            tokens.append(block)
        else:
            tokens.extend(block[i : i + 2] for i in range(len(block) - 1))
    return tokens


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文约 1 字符 1 token，其他约 4 字符 1 token。"""
    cjk = sum(1 for ch in text if "\u3400" <= ch <= "\u9fff")
    other = max(0, len(text) - cjk)
    return max(1, cjk + math.ceil(other / 4))
