"""离线评测：Recall@Top-K、Precision@Top-K、MRR、成本对比。"""
from __future__ import annotations

import json
import pathlib

from .answer import AnswerEngine
from .baseline import estimate_full_doc_cost
from .config import Config
from .documents import load_documents
from .search import HybridSearcher
from .tokenizer import estimate_tokens
from .vector_store import load_index


def _format_number(value: float) -> str:
    if value is None:
        return "N/A"
    return f"{value:.3f}"


def run_eval(
    config: Config,
    eval_path: pathlib.Path,
    output_dir: pathlib.Path,
    top_k: int | None = None,
) -> dict:
    top_k = top_k or config.top_k
    index_data = load_index(config.index_path)
    if index_data is None:
        raise RuntimeError(f"索引不存在: {config.index_path}，请先运行 python scripts/build_index.py")
    searcher = HybridSearcher(config, index_data)
    answer_engine = AnswerEngine(config, searcher)
    documents = load_documents(config.docs_dir)

    with eval_path.open("r", encoding="utf-8") as handle:
        items = json.load(handle)

    rows: list[dict] = []
    for item in items:
        query = item["query"]
        expected_docs = item.get("expected_docs", [])
        expected_keywords = item.get("expected_keywords", [])
        results = answer_engine.retrieve(query, top_k=top_k)
        retrieved_ids = [result.doc_id for result in results]
        expected_set = set(expected_docs)
        hit_docs: dict[str, int] = {}
        for rank, result in enumerate(results, start=1):
            if result.doc_id in expected_set and result.doc_id not in hit_docs:
                hit_docs[result.doc_id] = rank

        recall = len(hit_docs) / len(expected_set) if expected_set else None
        top_k_ids = list(dict.fromkeys(retrieved_ids[:top_k]))
        precision = len([doc for doc in top_k_ids if doc in expected_set]) / top_k
        mrr = 1.0 / min(hit_docs.values()) if hit_docs else 0.0

        snippet_text = "".join(result.text for result in results)
        if expected_keywords:
            answer_hit = any(keyword in snippet_text for keyword in expected_keywords)
        else:
            answer_hit = None

        rag_tokens = sum(estimate_tokens(result.text) for result in results)
        rag_cost = (
            rag_tokens / 1000 * config.input_cost_per_1k
            + 300 / 1000 * config.output_cost_per_1k
        )
        full_cost = estimate_full_doc_cost(config, query, documents)

        rows.append(
            {
                "id": item["id"],
                "category": item.get("category", "normal"),
                "query": query,
                "expected_docs": expected_docs,
                "expected_keywords": expected_keywords,
                "recall_at_top_k": recall,
                "precision_at_top_k": precision,
                "mrr": mrr,
                "answer_hit": answer_hit,
                "top_docs": retrieved_ids[:top_k],
                "rag_input_tokens": rag_tokens,
                "rag_cost": round(rag_cost, 6),
                "full_input_tokens": full_cost["input_tokens_estimate"],
                "full_cost": full_cost["total_cost_estimate"],
                "cost_ratio": round(full_cost["total_cost_estimate"] / max(rag_cost, 1e-9), 2),
            }
        )

    categories = sorted({row["category"] for row in rows})
    summary: dict[str, dict] = {}
    for category in categories:
        group = [row for row in rows if row["category"] == category]
        recalls = [row["recall_at_top_k"] for row in group if row["recall_at_top_k"] is not None]
        hits = [row["answer_hit"] for row in group if row["answer_hit"] is not None]
        summary[category] = {
            "count": len(group),
            "avg_recall_at_top_k": sum(recalls) / len(recalls) if recalls else None,
            "avg_precision_at_top_k": sum(row["precision_at_top_k"] for row in group) / len(group),
            "avg_mrr": sum(row["mrr"] for row in group) / len(group),
            "answer_hit_rate": sum(hits) / len(hits) if hits else None,
            "avg_rag_tokens": sum(row["rag_input_tokens"] for row in group) / len(group),
            "avg_full_tokens": sum(row["full_input_tokens"] for row in group) / len(group),
            "avg_cost_ratio": sum(row["cost_ratio"] for row in group) / len(group),
        }

    all_recalls = [row["recall_at_top_k"] for row in rows if row["recall_at_top_k"] is not None]
    all_hits = [row["answer_hit"] for row in rows if row["answer_hit"] is not None]
    overall = {
        "count": len(rows),
        "top_k": top_k,
        "avg_recall_at_top_k": sum(all_recalls) / len(all_recalls) if all_recalls else None,
        "avg_precision_at_top_k": sum(row["precision_at_top_k"] for row in rows) / len(rows),
        "avg_mrr": sum(row["mrr"] for row in rows) / len(rows),
        "answer_hit_rate": sum(all_hits) / len(all_hits) if all_hits else None,
        "avg_rag_tokens": sum(row["rag_input_tokens"] for row in rows) / len(rows),
        "avg_full_tokens": sum(row["full_input_tokens"] for row in rows) / len(rows),
        "avg_cost_ratio": sum(row["cost_ratio"] for row in rows) / len(rows),
        "embedding_backend": searcher.backend_name,
        "index_docs": searcher.stats["docs"],
        "index_chunks": searcher.stats["chunks"],
    }
    result = {"overall": overall, "by_category": summary, "rows": rows}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _write_report(output_dir, result)
    return result


def _write_report(output_dir: pathlib.Path, result: dict) -> None:
    overall = result["overall"]
    lines = [
        "# 评测报告",
        "",
        f"- 评测条目：{overall['count']}",
        f"- 索引规模：{overall['index_docs']} 篇文档 / {overall['index_chunks']} 个片段",
        f"- 嵌入后端：{overall['embedding_backend']}",
        f"- 评测 Top-K：{overall['top_k']}",
        "",
        "## 总体指标",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| Recall@Top-K | {_format_number(overall['avg_recall_at_top_k'])} |",
        f"| Precision@Top-K | {_format_number(overall['avg_precision_at_top_k'])} |",
        f"| MRR | {_format_number(overall['avg_mrr'])} |",
        f"| 片段命中关键词率 | {_format_number(overall['answer_hit_rate'])} |",
        f"| RAG 平均输入 tokens | {overall['avg_rag_tokens']:.0f} |",
        f"| 全量文档平均输入 tokens | {overall['avg_full_tokens']:.0f} |",
        f"| 全量/检索 成本比 | {overall['avg_cost_ratio']:.1f}x |",
        "",
        "## 分类指标",
        "",
        "| 类别 | 条数 | Recall@Top-K | Precision@Top-K | MRR | 成本比 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for category, metrics in result["by_category"].items():
        lines.append(
            f"| {category} | {metrics['count']} | "
            f"{_format_number(metrics['avg_recall_at_top_k'])} | "
            f"{_format_number(metrics['avg_precision_at_top_k'])} | "
            f"{_format_number(metrics['avg_mrr'])} | "
            f"{metrics['avg_cost_ratio']:.1f}x |"
        )
    lines += [
        "",
        "## 说明",
        "",
        "- 评测使用配置中的嵌入后端与检索管线；当前配置为本地 bge-m3 嵌入 + 混合检索 Top 20 + bge-reranker-v2-m3 精排 Top 3。",
        "- 成本对比为估算值：按配置中的每千 token 单价与 300 输出 token 计算。",
        "- 无答案类条目不参与 Recall/关键词命中统计，用于检查“查不到时不乱答”。",
        "",
    ]
    (output_dir / "eval_report.md").write_text("\n".join(lines), encoding="utf-8")
