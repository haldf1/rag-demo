"""启动本地 Web 演示。"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag_demo.cli import server  # noqa: E402
from rag_demo.config import get_config  # noqa: E402


if __name__ == "__main__":
    server(get_config())
