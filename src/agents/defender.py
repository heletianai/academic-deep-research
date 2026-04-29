"""
DefenderAgent（蓝方）：先搜再答，回应 Critic 质疑或主动承认修正。

Stage 2 红蓝对抗第二环。会调用 ArXiv 检索补充证据。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.llm_utils import chat_with_retry
from src.prompts.defender import DEFENDER_SYSTEM_PROMPT, DEFENDER_USER_TEMPLATE


class DefenderAgent:
    """蓝方：先搜再答 — 有证据则反驳，无证据则承认。"""

    def __init__(
        self,
        llm_client: OpenAI,
        arxiv_tool: Any,
        model: str = "deepseek/deepseek-v4-flash",
        search_per_critique: int = 3,
    ) -> None:
        self.llm = llm_client
        self.arxiv = arxiv_tool
        self.model = model
        self.search_per_critique = search_per_critique

    # --- 内部：拼检索 query 跑一轮 ArXiv ---
    def _gather_evidence(
        self, critique: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        """
        针对每条 critique 跑一次 ArXiv 检索，去重汇总。

        Returns:
            (all_papers, per_critique_papers)
            - all_papers: 去重后的所有证据 paper
            - per_critique_papers: dict[critique_str, list[paper]] 用于上下文展示
        """
        seen_ids: set[str] = set()
        all_papers: list[dict[str, Any]] = []
        per_critique: dict[str, list[dict[str, Any]]] = {}

        # 把所有维度 critique 拍平
        flat_critiques: list[str] = []
        for dim in ("factual", "logical", "citation"):
            flat_critiques.extend(critique.get(dim, []))

        for c in flat_critiques:
            try:
                papers = self.arxiv.search(c, top_k=self.search_per_critique)
            except Exception as e:
                papers = []
            per_critique[c] = papers
            for p in papers:
                pid = p.get("arxiv_id")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_papers.append(p)
        return all_papers, per_critique

    @staticmethod
    def _format_search_results(
        per_critique: dict[str, list[dict[str, Any]]]
    ) -> str:
        if not per_critique:
            return "(no critiques to search)"
        lines: list[str] = []
        for c, papers in per_critique.items():
            lines.append(f"\nFor critique: {c}")
            if not papers:
                lines.append("  (no relevant papers found)")
                continue
            for p in papers:
                lines.append(
                    f"  - [{p['arxiv_id']}] {p['title']}\n"
                    f"    {p['abstract'][:200]}..."
                )
        return "\n".join(lines)

    def run(
        self,
        draft_text: str,
        critique: dict[str, Any],
        round_num: int = 1,
    ) -> dict[str, Any]:
        """
        回应 Critic 质疑（先搜再答）。

        Args:
            draft_text: 当前草稿
            critique: Critic 输出 {"factual": [...], "logical": [...], "citation": [...]}
            round_num: 当前辩论轮次

        Returns:
            {
                "responses": [...],
                "conceded_points": [...],
                "revised_sections": {"background": "...", ...},
                "evidence_papers": [...]   # 本轮检索到的所有 paper（追溯用）
            }
        """
        # 1. 检索证据
        all_papers, per_critique = self._gather_evidence(critique)
        search_results_str = self._format_search_results(per_critique)

        # 2. 拼 prompt
        user = DEFENDER_USER_TEMPLATE.format(
            draft_text=draft_text,
            round_num=round_num,
            factual_critiques=json.dumps(critique.get("factual", []), ensure_ascii=False),
            logical_critiques=json.dumps(critique.get("logical", []), ensure_ascii=False),
            citation_critiques=json.dumps(critique.get("citation", []), ensure_ascii=False),
            search_results=search_results_str,
        )

        # 3. 调 LLM
        content = chat_with_retry(
            self.llm,
            model=self.model,
            messages=[
                {"role": "system", "content": DEFENDER_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2500,
        )
        try:
            response = json.loads(content)
        except json.JSONDecodeError:
            response = {
                "responses": [],
                "conceded_points": [],
                "revised_sections": {},
                "_raw": content,
                "_parse_error": True,
            }

        # 4. 字段保护 + 注入证据
        response.setdefault("responses", [])
        response.setdefault("conceded_points", [])
        response.setdefault("revised_sections", {})
        response["evidence_papers"] = all_papers
        return response

    @staticmethod
    def apply_revisions(
        original_draft: dict[str, Any], defender_response: dict[str, Any]
    ) -> dict[str, Any]:
        """
        把 Defender 的 revised_sections 应用到原始 draft，生成下一轮的 draft。

        简单策略：哪个 section 有 revision 就替换；没有则保留。
        """
        revised = dict(original_draft)
        revisions = defender_response.get("revised_sections", {}) or {}
        for sec in ("background", "methods", "findings"):
            new_text = revisions.get(sec, "").strip()
            if new_text:
                revised[sec] = new_text

        # 加入新引用（去重）
        existing_ids = {c.get("arxiv_id") for c in revised.get("citations", [])}
        for p in defender_response.get("evidence_papers", []):
            if p.get("arxiv_id") not in existing_ids:
                revised.setdefault("citations", []).append(
                    {
                        "arxiv_id": p["arxiv_id"],
                        "title": p["title"],
                        "url": p.get("url", ""),
                    }
                )
                existing_ids.add(p["arxiv_id"])
        return revised
