"""
ResearcherAgent：调 ArXiv 检索 → LLM 综合 → 出结构化初稿。

Stage 1 核心组件。Stage 2 红蓝对抗的输入来源。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.llm_utils import chat_with_retry


RESEARCHER_SYSTEM_PROMPT = """\
You are an academic researcher. Given a research question and a list of arXiv papers
(with titles, abstracts, and arxiv_ids), produce a structured first-draft survey.

Hard rules:
- Cite papers ONLY by their arxiv_id (e.g., [2305.14325]) provided in the input.
  Do NOT invent paper titles, authors, or arxiv_ids.
- If the provided papers do not cover an aspect, say "未在检索结果中找到相关论文" — do not fabricate.
- Output language: 中文为主，技术术语保留英文。
- Be concrete; avoid vague phrases like "many studies show".

Output format (strict JSON):
{
  "background": "200-400字，研究问题的领域背景与重要性",
  "methods": "300-500字，已有方法分类总结，每个方法标注[arxiv_id]",
  "findings": "200-400字，主要发现与未解决问题",
  "citations": [
    {"arxiv_id": "...", "title": "...", "url": "..."}
  ]
}
"""


class ResearcherAgent:
    """Stage 1 — 单 Researcher Agent，单源 ArXiv。"""

    def __init__(
        self,
        llm_client: OpenAI,
        arxiv_tool: Any,
        model: str = "deepseek/deepseek-v4-flash",
        top_k: int = 5,
    ) -> None:
        self.llm = llm_client
        self.arxiv = arxiv_tool
        self.model = model
        self.top_k = top_k

    def run(self, query: str) -> dict[str, Any]:
        # 1. 检索
        papers = self.arxiv.search(query, top_k=self.top_k)
        if not papers:
            return {
                "background": "ArXiv 检索未返回相关论文。",
                "methods": "",
                "findings": "",
                "citations": [],
                "raw_papers": [],
            }

        # 2. 拼上下文
        papers_str = "\n\n".join(
            f"[{p['arxiv_id']}] {p['title']}\n"
            f"Authors: {', '.join(p['authors'][:3])}{' et al.' if len(p['authors']) > 3 else ''}\n"
            f"Abstract: {p['abstract']}"
            for p in papers
        )
        user_prompt = (
            f"Research question:\n{query}\n\n"
            f"Retrieved papers (top-{len(papers)} from arXiv):\n\n{papers_str}\n\n"
            "Generate the structured draft now."
        )

        # 3. LLM 综合（强制 JSON）
        content = chat_with_retry(
            self.llm,
            model=self.model,
            messages=[
                {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2000,
        )
        try:
            draft = json.loads(content)
        except json.JSONDecodeError:
            draft = {"raw": content, "parse_error": True}

        # 4. 注入原始 papers（供下游 Critic / Defender 用）
        draft["raw_papers"] = papers
        return draft

    def render_markdown(self, draft: dict[str, Any]) -> str:
        """把 dict 初稿渲染成 markdown 文档（便于人工审阅 + Stage 2 输入）。"""
        if "parse_error" in draft:
            return f"# 研究初稿（JSON 解析失败）\n\n{draft.get('raw', '')}"

        cites = draft.get("citations", [])
        cite_lines = "\n".join(
            f"- [{c['arxiv_id']}] {c['title']} — {c.get('url', '')}"
            for c in cites
        )
        return (
            "# 研究初稿（Researcher Agent / Stage 1）\n\n"
            "## 背景\n\n"
            f"{draft.get('background', '')}\n\n"
            "## 方法综述\n\n"
            f"{draft.get('methods', '')}\n\n"
            "## 主要发现\n\n"
            f"{draft.get('findings', '')}\n\n"
            "## 引用\n\n"
            f"{cite_lines}\n"
        )
