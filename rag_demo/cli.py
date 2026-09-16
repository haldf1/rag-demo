"""命令行入口：build / query / eval / server / baseline。"""
from __future__ import annotations

import argparse
import json
import pathlib

from .answer import AnswerEngine
from .baseline import estimate_full_doc_cost
from .chunker import chunk_documents
from .config import get_config
from .documents import load_documents
from .embeddings import get_embedding_backend
from .eval_runner import run_eval
from .search import HybridSearcher
from .vector_store import build_index_data, load_index, save_index


def build(config) -> None:
    documents = load_documents(config.docs_dir)
    if not documents:
        print(f"目录中没有可解析文档: {config.docs_dir}")
        return
    chunks = chunk_documents(documents, config.chunk_size, config.chunk_overlap)
    backend, backend_name = get_embedding_backend(config)
    print(f"嵌入后端: {backend_name} | 文档: {len(documents)} | 片段: {len(chunks)}")
    vectors = backend.embed([chunk.text for chunk in chunks])
    index_data = build_index_data(documents, chunks, vectors, backend_name)
    save_index(config.index_path, index_data)
    print(f"索引已保存: {config.index_path}")


def query(config, question: str) -> None:
    index_data = load_index(config.index_path)
    if index_data is None:
        raise SystemExit("索引不存在，请先运行 python scripts/build_index.py")
    searcher = HybridSearcher(config, index_data)
    engine = AnswerEngine(config, searcher)
    response = engine.answer(question)
    print(f"答案来源: {response['used_backend']} | 耗时: {response['latency_ms']} ms")
    print("=" * 60)
    print(response["answer"])
    print("=" * 60)
    print("命中片段:")
    for result in response["results"]:
        print(
            f"#{result['rank']} 《{result['doc_title']}》"
            + (f" {result['heading']}" if result["heading"] else "")
        )
        print(result["text"][:160].replace("\n", " "))
        print()


def eval_command(config, eval_path: pathlib.Path) -> None:
    output_dir = eval_path.parent / "results"
    result = run_eval(config, eval_path, output_dir)
    print(json.dumps(result["overall"], ensure_ascii=False, indent=2))
    print(f"报告已输出: {output_dir / 'eval_report.md'}")


def server(config) -> None:
    from .ui_server import serve

    serve(config)


def baseline(config, question: str) -> None:
    documents = load_documents(config.docs_dir)
    cost = estimate_full_doc_cost(config, question, documents)
    print(f"全量文档方案估算（输入 {cost['input_tokens_estimate']} tokens）：")
    print(json.dumps(cost, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="最小 RAG 原型")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="解析文档并构建索引")
    query_parser = sub.add_parser("query", help="检索并回答")
    query_parser.add_argument("question", nargs="+")
    eval_parser = sub.add_parser("eval", help="运行评测")
    eval_parser.add_argument("--eval-file", default="eval/eval_set.json")
    server_parser = sub.add_parser("server", help="启动本地 Web 演示")
    server_parser.add_argument("--port", type=int, default=None)
    baseline_parser = sub.add_parser("baseline", help="估算旧方案全量喂文档成本")
    baseline_parser.add_argument("question", nargs="+")
    args = parser.parse_args(argv)

    config = get_config()
    if args.port:
        config.ui_port = args.port
    if args.command == "build":
        build(config)
    elif args.command == "query":
        query(config, " ".join(args.question))
    elif args.command == "eval":
        eval_command(config, pathlib.Path(args.eval_file))
    elif args.command == "server":
        server(config)
    elif args.command == "baseline":
        baseline(config, " ".join(args.question))


if __name__ == "__main__":
    main()
