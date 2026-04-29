"""
ArXiv 检索工具：直接调用 arxiv.org/api（Stage 1 baseline）。

Stage 2/3 升级路径：换成 MCP server 封装（保持接口一致即可）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import arxiv


class ArXivSearch:
    """ArXiv 检索工具，返回 list[dict]，字段稳定供 Researcher 使用。"""

    def __init__(self, top_k: int = 5) -> None:
        self.top_k = top_k
        self._client = arxiv.Client(page_size=top_k, delay_seconds=3.0, num_retries=3)

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        k = top_k or self.top_k
        s = arxiv.Search(
            query=query,
            max_results=k,
            sort_by=arxiv.SortCriterion.Relevance,
        )
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
        return results


if __name__ == "__main__":
    tool = ArXivSearch(top_k=3)
    papers = tool.search("multi-agent debate LLM hallucination")
    for i, p in enumerate(papers, 1):
        print(f"[{i}] {p['arxiv_id']} | {p['title']}")
        print(f"    {p['abstract'][:150]}...")
        print()
