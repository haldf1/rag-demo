"""冒烟测试：用 5 个真实问题验证检索链路。"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag_demo.config import get_config  # noqa: E402
from rag_demo.search import HybridSearcher  # noqa: E402
from rag_demo.vector_store import load_index  # noqa: E402


QUESTIONS = [
    "试用期一般是多长时间？",
    "出差住宿一晚最多能报销多少钱？",
    "客服 P0 工单的响应时限是多少？",
    "第 76 周周报中 3 号机房温度异常的原因是什么？",
    "公司对密码设置有什么要求？",
]


def main() -> None:
    config = get_config()
    index_data = load_index(config.index_path)
    if index_data is None:
        raise SystemExit("索引不存在，请先运行 python scripts/build_index.py")
    searcher = HybridSearcher(config, index_data)
    for question in QUESTIONS:
        results = searcher.search(question, top_k=3)
        print(f"Q: {question}")
        for result in results:
            print(
                f"  #{result.rank} 《{result.doc_title}》"
                + (f" {result.heading}" if result.heading else "")
            )
        print()


if __name__ == "__main__":
    main()
