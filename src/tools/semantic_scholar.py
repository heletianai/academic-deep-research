"""
Semantic Scholar MCP 工具封装：Stage 3 第二数据源。

通过 Semantic Scholar MCP server 补充 ArXiv 未收录文献，
提供引用关系图谱（cited-by / references）。
"""

from __future__ import annotations

from typing import Any


class SemanticScholarSearch:
    """
    Semantic Scholar 检索工具（Stage 3，MCP-First）。

    与 ArXivSearch 接口对齐，返回同一格式，
    额外提供 citation_count 和 references 字段。
    """

    def __init__(self, mcp_client: Any, top_k: int = 5) -> None:
        self.mcp_client = mcp_client
        self.top_k = top_k

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        执行 Semantic Scholar 文献检索。

        Args:
            query: 检索关键词

        Returns:
            文献列表，含 citation_count / references 额外字段
        """
        raise NotImplementedError("Stage 3 待实现：SemanticScholarSearch.search()")

    def get_references(self, paper_id: str) -> list[dict[str, Any]]:
        """
        获取指定论文的引用图谱（被引 + 参考）。

        Args:
            paper_id: Semantic Scholar paper ID

        Returns:
            引用关系列表
        """
        raise NotImplementedError("Stage 3 待实现：SemanticScholarSearch.get_references()")
