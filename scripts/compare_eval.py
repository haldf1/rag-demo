"""对比两份评测 metrics.json，生成 comparison.md。"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _overall_row(overall: dict) -> dict:
    return {
        "count": overall["count"],
        "backend": overall["embedding_backend"],
        "recall": overall["avg_recall_at_top_k"],
        "precision": overall["avg_precision_at_top_k"],
        "mrr": overall["avg_mrr"],
        "hit": overall["answer_hit_rate"],
        "rag_tokens": overall["avg_rag_tokens"],
        "cost_ratio": overall["avg_cost_ratio"],
    }


def _fmt(value, fmt: str) -> str:
    return "N/A" if value is None else fmt.format(value)


def compare(old_path: pathlib.Path, new_path: pathlib.Path, output_path: pathlib.Path) -> str:
    with old_path.open("r", encoding="utf-8") as handle:
        old_data = json.load(handle)
    with new_path.open("r", encoding="utf-8") as handle:
        new_data = json.load(handle)
    old = _overall_row(old_data["overall"])
    new = _overall_row(new_data["overall"])

    lines = [
        "# 新旧评测对比",
        "",
        f"| 项目 | 旧方案（{old['count']} 条 / {old['backend']}） | "
        f"新方案（{new['count']} 条 / {new['backend']}） |",
        "| --- | --- | --- |",
    ]
    specs = [
        ("评测条目", "count", "{:.0f}"),
        ("Recall@Top-K", "recall", "{:.3f}"),
        ("Precision@Top-K", "precision", "{:.3f}"),
        ("MRR", "mrr", "{:.3f}"),
        ("片段命中关键词率", "hit", "{:.3f}"),
        ("RAG 平均输入 tokens", "rag_tokens", "{:.0f}"),
        ("全量/检索成本比", "cost_ratio", "{:.1f}x"),
    ]
    for label, key, fmt in specs:
        lines.append(f"| {label} | {_fmt(old[key], fmt)} | {_fmt(new[key], fmt)} |")

    lines += [
        "",
        "## 分类指标（新方案）",
        "",
        "| 类别 | 条数 | Recall@Top-K | Precision@Top-K | MRR | 成本比 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for category, metrics in sorted(new_data["by_category"].items()):
        lines.append(
            f"| {category} | {metrics['count']} | "
            f"{_fmt(metrics['avg_recall_at_top_k'], '{:.3f}')} | "
            f"{_fmt(metrics['avg_precision_at_top_k'], '{:.3f}')} | "
            f"{_fmt(metrics['avg_mrr'], '{:.3f}')} | "
            f"{metrics['avg_cost_ratio']:.1f}x |"
        )
    text = "\n".join(lines) + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--old",
        type=pathlib.Path,
        default=ROOT / "eval" / "results" / "metrics_baseline_24_hash.json",
    )
    parser.add_argument(
        "--new",
        type=pathlib.Path,
        default=ROOT / "eval" / "results" / "metrics.json",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=ROOT / "eval" / "results" / "comparison.md",
    )
    args = parser.parse_args()
    print(compare(args.old, args.new, args.output))


if __name__ == "__main__":
    main()
