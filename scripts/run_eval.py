"""运行离线评测并生成指标报告。"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag_demo.cli import eval_command  # noqa: E402
from rag_demo.config import get_config  # noqa: E402


if __name__ == "__main__":
    eval_command(get_config(), ROOT / "eval" / "eval_set.json")
