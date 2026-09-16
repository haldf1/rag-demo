"""旧方案基线模拟：整篇文档 + 摘要全量喂给 LLM。"""
from __future__ import annotations

from .config import Config
from .documents import Document
from .tokenizer import estimate_tokens

SUMMARY_CHARS = 200
FULL_TEXT_CAP = 8000


def build_full_doc_prompt(query: str, documents: list[Document]) -> str:
    lines = [
        f"问题：{query}",
        "",
        "以下是知识库全部文档（每篇附自动摘要与正文）。请结合全文整理回答。",
        "",
    ]
    for index, doc in enumerate(documents, start=1):
        summary = doc.text[:SUMMARY_CHARS].replace("\n", " ")
        body = doc.text[:FULL_TEXT_CAP]
        if len(doc.text) > FULL_TEXT_CAP:
            body += "\n…（正文过长，已截断）"
        lines.append(f"## 文档{index}《{doc.title}》")
        lines.append(f"摘要：{summary}")
        lines.append("正文：")
        lines.append(body)
        lines.append("")
    return "\n".join(lines)


def estimate_full_doc_cost(config: Config, query: str, documents: list[Document]) -> dict:
    prompt = build_full_doc_prompt(query, documents)
    input_tokens = estimate_tokens(prompt) + estimate_tokens(query)
    output_tokens = 300
    input_cost = input_tokens / 1000 * config.input_cost_per_1k
    output_cost = output_tokens / 1000 * config.output_cost_per_1k
    return {
        "prompt_chars": len(prompt),
        "input_tokens_estimate": input_tokens,
        "output_tokens_estimate": output_tokens,
        "input_cost_estimate": round(input_cost, 6),
        "output_cost_estimate": round(output_cost, 6),
        "total_cost_estimate": round(input_cost + output_cost, 6),
        "risk": "文档多或篇幅长时上下文超限、耗时长、费用高",
    }
