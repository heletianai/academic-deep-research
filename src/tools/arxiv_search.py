"""
ArXiv 检索工具：直接调用 arxiv.org/api（Stage 1 baseline）。

Stage 2/3 升级路径：换成 MCP server 封装（保持接口一致即可）。

2026.4.30 升级：加 papers 缓存 + 429/503 退避重试（应对 ArXiv API 全局限速）。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import arxiv


# Papers 缓存目录（跨 run 共享，加速 ablation 多 seed）
ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT / "benchmarks" / "papers_cache"


class ArXivSearch:
    """ArXiv 检索工具，返回 list[dict]，字段稳定供 Researcher 使用。"""

    def __init__(self, top_k: int = 5, use_cache: bool = True, cache_only: bool | None = None) -> None:
        self.top_k = top_k
        self.use_cache = use_cache
        # cache_only: env ARXIV_CACHE_ONLY=1 时启用，cache miss 直接返 []，不打 API
        if cache_only is None:
            import os as _os
            cache_only = _os.getenv("ARXIV_CACHE_ONLY", "").lower() in ("1", "true", "yes")
        self.cache_only = cache_only
        # 客户端层退避：page_size 拉大、delay 拉大、num_retries 增大
        self._client = arxiv.Client(page_size=top_k, delay_seconds=5.0, num_retries=5)
        if use_cache:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, query: str, top_k: int) -> Path:
        """query 的哈希作为缓存 key（避免文件名特殊字符）。"""
        import hashlib

        h = hashlib.md5(f"{query}|{top_k}".encode()).hexdigest()[:16]
        return CACHE_DIR / f"arxiv_{h}.json"

    def _read_cache(self, query: str, top_k: int) -> list[dict[str, Any]] | None:
        if not self.use_cache:
            return None
        path = self._cache_key(query, top_k)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def _write_cache(self, query: str, top_k: int, results: list[dict[str, Any]]) -> None:
        if not self.use_cache or not results:
            return
        path = self._cache_key(query, top_k)
        try:
            path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or self.top_k

        # 1. 缓存命中 → 直接返回（ablation 多 seed 大量复用）
        cached = self._read_cache(query, k)
        if cached:
            return cached

        # 1.5 cache_only 模式：miss 直接返空，不打 API（避免触发 ArXiv IP 限速）
        if self.cache_only:
            return []

        # 2. 调 API + 退避重试
        s = arxiv.Search(
            query=query,
            max_results=k,
            sort_by=arxiv.SortCriterion.Relevance,
        )

        last_err: Exception | None = None
        for attempt in range(1, 6):  # 最多 5 次外层重试
            try:
                results: list[dict[str, Any]] = []
                for paper in self._client.results(s):
                    results.append(
                        {
                            "arxiv_id": paper.get_short_id(),
                            "title": paper.title.strip(),
                            "abstract": paper.summary.strip().replace("\n", " "),
                            "authors": [a.name for a in paper.authors],
                            "url": paper.entry_id,
                            "pdf_url": paper.pdf_url,
                            "published": paper.published.isoformat() if isinstance(paper.published, datetime) else str(paper.published),
                            "categories": paper.categories,
                        }
                    )
                # 3. 写缓存
                self._write_cache(query, k, results)
                return results
            except Exception as e:
                last_err = e
                err_str = str(e)
                # 429 / 503 / 网络错误 → 指数退避
                if "429" in err_str or "503" in err_str or "rate" in err_str.lower():
                    backoff = 30 * (2 ** (attempt - 1))  # 30s / 60s / 120s / 240s / 480s
                    print(f"  [ArXiv] {attempt}/5 限速，退避 {backoff}s ...")
                    time.sleep(backoff)
                else:
                    # 非限速错误，短暂退避后重试
                    print(f"  [ArXiv] {attempt}/5 错误 {err_str[:80]}，等 10s ...")
                    time.sleep(10)

        # 全部重试失败 → 返回空（Researcher 会处理空 papers 情况）
        print(f"  [ArXiv] 全部重试失败，返回空: {last_err}")
        return []


if __name__ == "__main__":
    tool = ArXivSearch(top_k=3)
    papers = tool.search("multi-agent debate LLM hallucination")
    for i, p in enumerate(papers, 1):
        print(f"[{i}] {p['arxiv_id']} | {p['title']}")
        print(f"    {p['abstract'][:150]}...")
        print()
