"""配置加载：默认值 + .env 覆盖，不依赖第三方库。"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent


def load_dotenv(path: pathlib.Path | None = None) -> None:
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


@dataclass
class Config:
    docs_dir: pathlib.Path
    index_path: pathlib.Path
    chunk_size: int = 400
    chunk_overlap: int = 60
    top_k: int = 8
    bm25_weight: float = 0.5
    vector_weight: float = 0.5
    rrf_k: int = 60
    rerank_enabled: bool = False
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    retrieve_top_n: int = 20
    embedding_backend: str = "auto"  # auto | hash | cloud | local
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    llm_direct_fallback: bool = True
    input_cost_per_1k: float = 0.002
    output_cost_per_1k: float = 0.008
    ui_host: str = "0.0.0.0"
    ui_port: int = 8765
    extra: dict = field(default_factory=dict)


def get_config() -> Config:
    load_dotenv()

    def env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def env_int(key: str, default: int) -> int:
        try:
            return int(os.environ.get(key, default))
        except (TypeError, ValueError):
            return default

    def env_float(key: str, default: float) -> float:
        try:
            return float(os.environ.get(key, default))
        except (TypeError, ValueError):
            return default

    def env_bool(key: str, default: bool) -> bool:
        value = os.environ.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    docs_dir = pathlib.Path(env("RAG_DOCS_DIR", str(BASE_DIR / "docs_input")))
    if not docs_dir.exists():
        docs_dir = BASE_DIR / "sample_docs"

    cfg = Config(
        docs_dir=docs_dir,
        index_path=pathlib.Path(
            env("RAG_INDEX_PATH", str(BASE_DIR / "data" / "index.json"))
        ),
        chunk_size=env_int("RAG_CHUNK_SIZE", 400),
        chunk_overlap=env_int("RAG_CHUNK_OVERLAP", 60),
        top_k=env_int("RAG_TOP_K", 8),
        bm25_weight=env_float("RAG_BM25_WEIGHT", 0.5),
        vector_weight=env_float("RAG_VECTOR_WEIGHT", 0.5),
        rrf_k=env_int("RAG_RRF_K", 60),
        rerank_enabled=env_bool("RAG_RERANK_ENABLED", False),
        rerank_model=env("RAG_RERANK_MODEL", "BAAI/bge-reranker-v2-m3"),
        retrieve_top_n=env_int("RAG_RETRIEVE_TOP_N", 20),
        embedding_backend=env("RAG_EMBEDDING_BACKEND", "auto"),
        embedding_model=env("RAG_EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_base_url=env("RAG_EMBEDDING_BASE_URL", "https://api.openai.com/v1"),
        embedding_api_key=env("RAG_EMBEDDING_API_KEY", ""),
        llm_model=env("RAG_LLM_MODEL", "gpt-4o-mini"),
        llm_base_url=env("RAG_LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=env("RAG_LLM_API_KEY", ""),
        llm_timeout_seconds=env_float("RAG_LLM_TIMEOUT_SECONDS", 30.0),
        llm_direct_fallback=env_bool("RAG_LLM_DIRECT_FALLBACK", True),
        input_cost_per_1k=env_float("RAG_INPUT_COST_PER_1K", 0.002),
        output_cost_per_1k=env_float("RAG_OUTPUT_COST_PER_1K", 0.008),
        ui_host=env("RAG_UI_HOST", "0.0.0.0"),
        ui_port=env_int("RAG_UI_PORT", 8765),
    )
    cfg.index_path.parent.mkdir(parents=True, exist_ok=True)
    return cfg
