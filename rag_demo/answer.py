"""基于检索片段的答案生成：优先云 LLM，离线时退化为模板答案。"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request

from .config import Config
from .reranker import Reranker
from .search import HybridSearcher, SearchResult
from .tokenizer import estimate_tokens


def _is_loopback_host(value: str) -> bool:
    try:
        parsed = urllib.parse.urlsplit(value if "://" in value else "//" + value)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _is_connection_refused(exc: Exception) -> bool:
    reason = getattr(exc, "reason", exc)
    winerror = getattr(reason, "winerror", None)
    errno = getattr(reason, "errno", None)
    text = str(reason).lower()
    return (
        isinstance(reason, ConnectionRefusedError)
        or winerror == 10061
        or errno in {61, 111}
        or "10061" in text
        or "refused" in text
        or "积极拒绝" in text
    )


def _active_proxy(base_url: str) -> str:
    scheme = urllib.parse.urlsplit(base_url).scheme.lower()
    proxies = urllib.request.getproxies()
    return proxies.get(scheme) or proxies.get("all") or ""


def _should_retry_direct(
    exc: Exception, base_url: str, direct_fallback: bool
) -> bool:
    if not direct_fallback or not _is_connection_refused(exc):
        return False
    proxy = _active_proxy(base_url)
    return bool(proxy and _is_loopback_host(proxy))


def _friendly_llm_error(exc: Exception, base_url: str, timeout: float) -> str:
    """把底层网络异常转换为适合展示的降级提示。"""
    if isinstance(exc, urllib.error.HTTPError):
        return f"LLM 服务返回 HTTP {exc.code}，已自动使用模板答案"

    reason = getattr(exc, "reason", exc)
    text = str(reason).lower()

    if _is_connection_refused(exc):
        if _is_loopback_host(base_url):
            return f"本地 LLM 代理未启动（{base_url}），已自动使用模板答案"
        return f"无法连接 LLM 服务（{base_url}），已自动使用模板答案"

    if isinstance(reason, TimeoutError) or "timed out" in text or "timeout" in text:
        return f"LLM 服务响应超时（{timeout:.0f} 秒），已自动使用模板答案"

    if isinstance(exc, RuntimeError):
        return str(exc)
    return "LLM 服务暂时不可用，已自动使用模板答案"


def _open_chat(
    request: urllib.request.Request,
    base_url: str,
    timeout: float,
    direct_fallback: bool,
):
    timeout = max(timeout, 1.0)
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except Exception as exc:  # noqa: BLE001
        if not _should_retry_direct(exc, base_url, direct_fallback):
            raise
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            response = opener.open(request, timeout=timeout)
        except Exception as direct_exc:  # noqa: BLE001
            raise RuntimeError(
                _friendly_llm_error(direct_exc, base_url, timeout)
            ) from direct_exc
        print("[info] 检测到本地代理不可用，已直连 LLM 服务")
        return response


def _call_chat(
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int = 800,
    timeout: float = 30.0,
    direct_fallback: bool = True,
) -> tuple[str, dict]:
    payload = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是企业内部知识库助手，回答必须基于给定资料并标注来源。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with _open_chat(request, base_url, timeout, direct_fallback) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"LLM 服务返回 HTTP {exc.code}，已自动使用模板答案"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("LLM 返回内容格式异常，已自动使用模板答案") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(_friendly_llm_error(exc, base_url, timeout)) from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("LLM 返回内容格式异常，已自动使用模板答案") from exc
    usage = data.get("usage", {})
    return content, usage


def build_prompt(query: str, results: list[SearchResult]) -> str:
    lines = [
        f"问题：{query}",
        "",
        "请只根据下面的检索片段回答；片段不足以回答时，明确说明知识库中没有找到答案。",
        "每条回答末尾用 [来源N] 标注依据。",
        "",
    ]
    for index, result in enumerate(results, start=1):
        heading = f"（{result.heading}）" if result.heading else ""
        lines.append(f"[来源{index}] 文档《{result.doc_title}》{heading}：")
        lines.append(result.text.strip())
        lines.append("")
    return "\n".join(lines)


def _template_answer(results: list[SearchResult], note: str | None = None) -> str:
    if note:
        lines = [f"以下为基于检索片段的答案草稿（{note}）：", ""]
        tail = "LLM 服务恢复后会自动切换回大模型回答。"
    else:
        lines = ["以下为基于检索片段的答案草稿（未配置 LLM，使用模板答案）：", ""]
        tail = "配置 LLM 后会自动切换到大模型回答。"
    for index, result in enumerate(results[:3], start=1):
        body = result.text.split("\n", 1)[-1].strip()
        point = body[:120] + ("…" if len(body) > 120 else "")
        lines.append(f"{index}. {point} [来源{index}]")
    lines.append("")
    lines.append(tail)
    return "\n".join(lines)


class AnswerEngine:
    def __init__(self, config: Config, searcher: HybridSearcher) -> None:
        self.config = config
        self.searcher = searcher
        self.reranker: Reranker | None = None

    def _get_reranker(self) -> Reranker:
        if self.reranker is None:
            self.reranker = Reranker(self.config.rerank_model)
        return self.reranker

    def retrieve(self, query: str, top_k: int | None = None) -> list[SearchResult]:
        final_k = top_k or self.config.top_k
        if self.config.rerank_enabled:
            candidates = self.searcher.search(query, top_k=self.config.retrieve_top_n)
            return self._get_reranker().rerank(query, candidates, final_k)
        return self.searcher.search(query, top_k=final_k)

    def answer(self, query: str) -> dict:
        started = time.perf_counter()
        results = self.retrieve(query)
        prompt = build_prompt(query, results)
        used_backend = "template"
        llm_status = "disabled"
        llm_note = "未配置 LLM，使用模板答案"
        answer_text = _template_answer(results)
        usage: dict = {}
        if self.config.llm_api_key:
            llm_status = "fallback"
            try:
                answer_text, usage = _call_chat(
                    self.config.llm_base_url,
                    self.config.llm_api_key,
                    self.config.llm_model,
                    prompt,
                    timeout=self.config.llm_timeout_seconds,
                    direct_fallback=self.config.llm_direct_fallback,
                )
                used_backend = "llm"
                llm_status = "ok"
                llm_note = ""
            except Exception as exc:  # noqa: BLE001
                llm_note = _friendly_llm_error(
                    exc,
                    self.config.llm_base_url,
                    self.config.llm_timeout_seconds,
                )
                answer_text = _template_answer(results, llm_note)
                print(f"[warn] LLM 调用失败，已降级为模板答案: {llm_note}")
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        citations = [
            {
                "doc_id": result.doc_id,
                "doc_title": result.doc_title,
                "chunk_id": result.chunk_id,
                "heading": result.heading,
                "snippet": result.text[:120],
            }
            for result in results
        ]
        return {
            "query": query,
            "answer": answer_text,
            "used_backend": used_backend,
            "llm_status": llm_status,
            "latency_ms": latency_ms,
            "results": [
                {
                    "rank": result.rank,
                    "doc_id": result.doc_id,
                    "doc_title": result.doc_title,
                    "heading": result.heading,
                    "text": result.text,
                    "score": round(result.score, 5),
                    "vector_score": round(result.vector_score, 5),
                    "bm25_score": round(result.bm25_score, 5),
                }
                for result in results
            ],
            "citations": citations,
            "usage": usage,
            "llm_note": llm_note,
            "prompt_tokens_estimate": estimate_tokens(prompt),
            "answer_tokens_estimate": estimate_tokens(answer_text),
        }
