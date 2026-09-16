"""索引存取：本地 JSON + numpy 向量，零运维；生产可替换为 Chroma/Qdrant。"""
from __future__ import annotations

import json
import pathlib
import time

import numpy as np


def document_record(document) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "source_path": document.source_path,
        "ext": document.ext,
        "char_count": document.char_count,
    }


def chunk_record(chunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "doc_title": chunk.doc_title,
        "heading": chunk.heading,
        "text": chunk.text,
        "char_count": chunk.char_count,
    }


def build_index_data_from_records(
    documents: list[dict],
    chunks: list[dict],
    vectors,
    backend_name: str,
) -> dict:
    vector_array = np.asarray(vectors, dtype=np.float32)
    if vector_array.size == 0:
        vector_array = np.zeros((0, 0), dtype=np.float32)
    dim = int(vector_array.shape[1]) if vector_array.ndim == 2 else 0
    return {
        "meta": {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "backend": backend_name,
            "dim": dim,
            "doc_count": len(documents),
            "chunk_count": len(chunks),
        },
        "documents": documents,
        "chunks": chunks,
        "vectors": {
            "backend": backend_name,
            "dim": dim,
            "data": vector_array.tolist(),
        },
    }


def build_index_data(
    documents, chunks, vectors: np.ndarray, backend_name: str
) -> dict:
    return build_index_data_from_records(
        [document_record(document) for document in documents],
        [chunk_record(chunk) for chunk in chunks],
        vectors,
        backend_name,
    )


def save_index(index_path: pathlib.Path, index_data: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index_data, handle, ensure_ascii=False, indent=1)


def load_index(index_path: pathlib.Path) -> dict | None:
    if not index_path.exists():
        return None
    with index_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
