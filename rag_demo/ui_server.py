"""零依赖 Web 演示：http.server 提供页面与查询 API。"""
from __future__ import annotations

import datetime
import json
import pathlib
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .answer import AnswerEngine
from .chunker import chunk_documents
from .documents import SUPPORTED_EXTS, load_document
from .search import HybridSearcher
from .vector_store import (
    build_index_data_from_records,
    chunk_record,
    document_record,
    load_index,
    save_index,
)

STATIC_DIR = pathlib.Path(__file__).resolve().parent / "static"
LOG_FILE = pathlib.Path(__file__).resolve().parent.parent / "_ui_server.log"
ALLOWED_UPLOAD_EXTS = set(SUPPORTED_EXTS)
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


class RagThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False


def _log(message: str) -> None:
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {message}"
    print(line, flush=True)
    try:
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _document_record(path: pathlib.Path) -> dict:
    stat = path.stat()
    return {
        "name": path.name,
        "extension": path.suffix.lstrip(".").upper(),
        "size": stat.st_size,
        "modified": datetime.datetime.fromtimestamp(
            stat.st_mtime
        ).astimezone().isoformat(timespec="seconds"),
    }


def serve(config) -> None:
    _log("正在加载索引和本地模型，首次启动约需 1-3 分钟...")
    index_data = load_index(config.index_path)
    if index_data is None:
        raise SystemExit("索引不存在，请先运行 python scripts/build_index.py")
    _log(
        f"索引已加载：{index_data['meta']['doc_count']} 篇文档 "
        f"/ {index_data['meta']['chunk_count']} 个片段"
    )
    searcher = HybridSearcher(config, index_data)
    engine = AnswerEngine(config, searcher)
    index_lock = threading.Lock()
    last_index_signature = ""

    def _indexable_files() -> list[pathlib.Path]:
        if not config.docs_dir.exists():
            return []
        return sorted(
            (
                path
                for path in config.docs_dir.iterdir()
                if path.is_file()
                and not path.name.startswith(".")
                and path.suffix.lower() in SUPPORTED_EXTS
            ),
            key=lambda item: item.name.casefold(),
        )

    def _disk_signature() -> tuple[tuple[str, int, int], ...]:
        return tuple(
            (path.name, path.stat().st_size, path.stat().st_mtime_ns)
            for path in _indexable_files()
        )

    def _indexed_names() -> set[str]:
        return {document["id"] for document in searcher.documents}

    def _sync_index_locked() -> bool:
        nonlocal last_index_signature
        current_signature = _disk_signature()
        current_map = {
            name: (size, modified)
            for name, size, modified in current_signature
        }
        last_map = {
            name: (size, modified)
            for name, size, modified in last_index_signature
        }
        disk_names = set(current_map)
        index_names = _indexed_names()
        remove_ids = index_names - disk_names
        changed_ids = {
            name
            for name in index_names & disk_names
            if current_map[name] != last_map.get(name)
        }
        upsert_ids = (disk_names - index_names) | changed_ids
        remove_ids |= changed_ids
        if not remove_ids and not upsert_ids:
            return False

        old_index = searcher.index
        old_chunks = old_index["chunks"]
        old_vectors = old_index["vectors"]["data"]
        keep_indices = [
            index
            for index, chunk in enumerate(old_chunks)
            if chunk["doc_id"] not in remove_ids
        ]
        documents = [
            document
            for document in old_index["documents"]
            if document["id"] not in remove_ids
        ]
        chunks = [old_chunks[index] for index in keep_indices]
        vectors = [old_vectors[index] for index in keep_indices]

        paths = {path.name: path for path in _indexable_files()}
        for name in sorted(upsert_ids):
            path = paths.get(name)
            if path is None:
                continue
            document = load_document(path)
            new_chunks = chunk_documents(
                [document],
                config.chunk_size,
                config.chunk_overlap,
            )
            new_vectors = (
                searcher.embeddings.embed([chunk.text for chunk in new_chunks])
                .tolist()
                if new_chunks
                else []
            )
            documents.append(document_record(document))
            chunks.extend(chunk_record(chunk) for chunk in new_chunks)
            vectors.extend(new_vectors)

        rebuilt = build_index_data_from_records(
            documents,
            chunks,
            vectors,
            searcher.backend_name,
        )
        rebuilt["meta"]["source_signature"] = [
            list(item) for item in current_signature
        ]
        save_index(config.index_path, rebuilt)
        searcher.reload(rebuilt)
        last_index_signature = current_signature
        _log(
            "检索索引已增量同步："
            f"新增/更新 {len(upsert_ids)} 篇，删除 {len(remove_ids)} 篇，"
            f"当前 {len(documents)} 篇文档 / {len(chunks)} 个片段"
        )
        return True

    def _ensure_index_synced() -> bool:
        with index_lock:
            return _sync_index_locked()

    stored_signature = index_data.get("meta", {}).get("source_signature", [])
    if stored_signature:
        last_index_signature = tuple(
            (str(name), int(size), int(modified))
            for name, size, modified in stored_signature
        )
    else:
        last_index_signature = _disk_signature()
    try:
        _ensure_index_synced()
    except Exception as exc:  # noqa: BLE001
        _log(f"启动时同步索引失败，继续使用现有索引: {exc}")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: A003
            _log(f"[ui] {self.address_string()} - {fmt % args}")

        def _send_json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/health":
                self._send_json(
                    {"status": "ok", **searcher.stats, "backend": engine.config.embedding_backend}
                )
                return
            if parsed.path == "/api/query":
                query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0]
                if not query.strip():
                    self._send_json({"error": "empty query"}, status=400)
                    return
                try:
                    _ensure_index_synced()
                except Exception as exc:  # noqa: BLE001
                    self._send_json(
                        {"error": f"检索索引同步失败: {exc}"},
                        status=500,
                    )
                    return
                try:
                    self._send_json(engine.answer(query))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"error": str(exc)}, status=500)
                return
            if parsed.path == "/api/documents":
                docs_dir = config.docs_dir
                if not docs_dir.exists():
                    self._send_json(
                        {"error": f"文档目录不存在: {docs_dir}"},
                        status=404,
                    )
                    return
                index_error = ""
                try:
                    _ensure_index_synced()
                except Exception as exc:  # noqa: BLE001
                    index_error = str(exc)
                    _log(f"文档列表触发索引同步失败: {exc}")
                try:
                    documents = []
                    files = (
                        path
                        for path in docs_dir.iterdir()
                        if path.is_file() and not path.name.startswith(".")
                    )
                    for path in sorted(files, key=lambda item: item.name.casefold()):
                        documents.append(_document_record(path))
                except OSError as exc:
                    self._send_json({"error": str(exc)}, status=500)
                    return
                self._send_json(
                    {
                        "directory": str(docs_dir),
                        "directory_name": docs_dir.name,
                        "count": len(documents),
                        "index_error": index_error,
                        "documents": documents,
                    }
                )
                return
            if parsed.path == "/style.css":
                css = STATIC_DIR / "style.css"
                if not css.exists():
                    self.send_response(404)
                    self.end_headers()
                    return
                body = css.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/css; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if parsed.path in ("/", "/index.html"):
                html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/documents/upload":
                self.send_response(404)
                self.end_headers()
                return

            raw_name = urllib.parse.parse_qs(parsed.query).get("name", [""])[0]
            safe_name = pathlib.Path(raw_name.replace("\\", "/")).name.strip()
            if not safe_name or safe_name in {".", ".."} or "\x00" in safe_name:
                self._send_json({"error": "文件名无效"}, status=400)
                return
            if pathlib.Path(safe_name).suffix.lower() not in ALLOWED_UPLOAD_EXTS:
                self._send_json({"error": "不支持的文档格式"}, status=400)
                return

            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length = 0
            if content_length <= 0:
                self._send_json({"error": "文件内容为空"}, status=400)
                return
            if content_length > MAX_UPLOAD_BYTES:
                self._send_json({"error": "文件超过 100 MB 限制"}, status=413)
                return

            body = self.rfile.read(content_length)
            if len(body) != content_length:
                self._send_json({"error": "文件上传不完整"}, status=400)
                return

            docs_dir = config.docs_dir
            try:
                docs_dir.mkdir(parents=True, exist_ok=True)
                target = docs_dir / safe_name
                with target.open("xb") as handle:
                    handle.write(body)
            except FileExistsError:
                self._send_json({"error": f"文档已存在: {safe_name}"}, status=409)
                return
            except OSError as exc:
                self._send_json({"error": str(exc)}, status=500)
                return

            try:
                load_document(target)
            except Exception as exc:  # noqa: BLE001
                target.unlink(missing_ok=True)
                self._send_json({"error": f"文档解析失败: {exc}"}, status=400)
                return

            try:
                _ensure_index_synced()
            except Exception as exc:  # noqa: BLE001
                target.unlink(missing_ok=True)
                self._send_json(
                    {"error": f"文档已取消，检索索引更新失败: {exc}"},
                    status=500,
                )
                return

            self._send_json(
                {
                    "ok": True,
                    "directory": str(docs_dir),
                    "indexed": True,
                    "document": _document_record(target),
                },
                status=201,
            )

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/api/documents":
                self.send_response(404)
                self.end_headers()
                return

            raw_name = urllib.parse.parse_qs(parsed.query).get("name", [""])[0]
            safe_name = pathlib.Path(raw_name.replace("\\", "/")).name.strip()
            if not safe_name or safe_name in {".", ".."} or "\x00" in safe_name:
                self._send_json({"error": "文件名无效"}, status=400)
                return

            target = config.docs_dir / safe_name
            if not target.exists() or not target.is_file():
                self._send_json({"error": f"文档不存在: {safe_name}"}, status=404)
                return
            try:
                target.unlink()
            except OSError as exc:
                self._send_json({"error": str(exc)}, status=500)
                return

            try:
                _ensure_index_synced()
            except Exception as exc:  # noqa: BLE001
                _log(f"删除后同步索引失败: {exc}")
                self._send_json(
                    {"error": f"文件已删除，但检索索引同步失败: {exc}"},
                    status=500,
                )
                return

            self._send_json({"ok": True, "deleted": safe_name, "indexed": True})

    try:
        server = RagThreadingHTTPServer((config.ui_host, config.ui_port), Handler)
    except OSError as exc:
        if getattr(exc, "winerror", None) == 10048 or getattr(exc, "errno", None) in {48, 98, 100}:
            raise SystemExit(
                f"端口 {config.ui_port} 已被占用，请关闭已有服务或修改 RAG_UI_PORT。"
            ) from None
        raise
    _log(f"RAG 演示已启动: http://{config.ui_host}:{config.ui_port}")
    _log("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
