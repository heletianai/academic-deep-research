"""
Semantic Scholar 检索：Stage 3 第二数据源。

Semantic Scholar Public API: https://api.semanticscholar.org/graph/v1
- 公开免费，无 API key 时 rate limit 100 req / 5min
- 返回字段更丰富（citationCount / references / influentialCitationCount）

接口与 ArXivSearch 对齐（list[dict]），便于多源并行调用。
"""

from __future__ import annotations

import time
from typing import Any

import requests


SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarSearch:
    """Semantic Scholar 检索（HTTP 直调，无外部依赖）。"""

    def __init__(
        self,
        top_k: int = 5,
        timeout: float = 15.0,
        backoff: float = 2.0,
    ) -> None:
        self.top_k = top_k
        self.timeout = timeout
        self.backoff = backoff
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "academic-deep-research/0.1"})

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """
        关键词检索。

        Returns:
            list[dict]，每条字段对齐 ArXivSearch:
                arxiv_id, title, abstract, authors, url, published, categories
            额外字段:
                citation_count, source="semantic_scholar"
        """
        k = top_k or self.top_k
        url = f"{SEMANTIC_SCHOLAR_API}/paper/search"
        params = {
            "query": query,
            "limit": k,
            "fields": "title,abstract,authors,year,citationCount,externalIds,url,venue",
        }

        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                if resp.status_code == 429:
                    print(f"  [SemanticScholar] 429，等 {self.backoff}s")
                    time.sleep(self.backoff)
                    self.backoff *= 2
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, ValueError) as e:
                if attempt == 2:
                    print(f"  [SemanticScholar] 失败 {e}，返回空")
                    return []
                time.sleep(self.backoff)
        else:
            return []

        results: list[dict[str, Any]] = []
        for p in data.get("data", []):
            ext = p.get("externalIds", {}) or {}
            arxiv_id = ext.get("ArXiv") or ""
            ss_id = p.get("paperId", "")
            doi = ext.get("DOI", "")
            paper_url = (
                f"https://arxiv.org/abs/{arxiv_id}"
                if arxiv_id
                else p.get("url") or f"https://www.semanticscholar.org/paper/{ss_id}"
            )

            results.append(
                {
                    "arxiv_id": arxiv_id or f"ss:{ss_id[:10]}",  # 没 arXiv 用 ss: 前缀
                    "title": (p.get("title") or "").strip(),
                    "abstract": (p.get("abstract") or "").strip().replace("\n", " "),
                    "authors": [a.get("name", "") for a in (p.get("authors") or [])],
                    "url": paper_url,
                    "pdf_url": "",
                    "published": str(p.get("year") or ""),
                    "categories": [p.get("venue", "")] if p.get("venue") else [],
                    "citation_count": p.get("citationCount", 0),
                    "source": "semantic_scholar",
                    "doi": doi,
                }
            )
        return results


class MultiSourceSearch:
    """
    多源并行检索：ArXiv + Semantic Scholar，按 arxiv_id 去重。

    Stage 3 的核心 - Researcher 用这个替代单源 ArXivSearch。
    """

    def __init__(self, arxiv_tool: Any, ss_tool: SemanticScholarSearch | None = None, top_k: int = 5) -> None:
        self.arxiv = arxiv_tool
        self.ss = ss_tool or SemanticScholarSearch(top_k=top_k)
        self.top_k = top_k

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or self.top_k

        # 各源取一半（向上取整）
        per_source = (k + 1) // 2

        try:
            arxiv_results = self.arxiv.search(query, top_k=per_source)
        except Exception as e:
            print(f"  [MultiSource] ArXiv 失败 {e}")
            arxiv_results = []

        try:
            ss_results = self.ss.search(query, top_k=per_source)
        except Exception as e:
            print(f"  [MultiSource] SemanticScholar 失败 {e}")
            ss_results = []

        # 标 source（ArXiv 没标过）
        for r in arxiv_results:
            r.setdefault("source", "arxiv")
            r.setdefault("citation_count", None)

        # SS 失败时 fallback：ArXiv 补足到 top_k
        if not ss_results and len(arxiv_results) < k:
            try:
                extra = self.arxiv.search(query, top_k=k - len(arxiv_results))
                # 排除已有
                existing = {r.get("arxiv_id") for r in arxiv_results}
                for r in extra:
                    if r.get("arxiv_id") not in existing:
                        r.setdefault("source", "arxiv")
                        r.setdefault("citation_count", None)
                        arxiv_results.append(r)
            except Exception:
                pass

        # 去重（按 arxiv_id），ArXiv 优先
        seen_ids: set[str] = set()
        merged: list[dict[str, Any]] = []
        for r in arxiv_results + ss_results:
            pid = r.get("arxiv_id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                merged.append(r)

        return merged[:k]


if __name__ == "__main__":
    tool = SemanticScholarSearch(top_k=3)
    papers = tool.search("multi-agent debate LLM hallucination")
    for i, p in enumerate(papers, 1):
        print(f"[{i}] {p['arxiv_id']} | {p['title'][:80]}")
        print(f"    citations={p['citation_count']} | year={p['published']}")
        print()
