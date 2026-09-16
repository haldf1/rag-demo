"""命令行检索示例：python scripts/query.py "你的问题" """
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag_demo.cli import query  # noqa: E402
from rag_demo.config import get_config  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("用法: python scripts/query.py \"你的问题\"")
    query(get_config(), " ".join(sys.argv[1:]))
