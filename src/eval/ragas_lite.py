"""
RAGAs-lite：自研轻量版 RAG 评估，DeepSeek-V4 当 judge。

为什么不用 RAGAs 官方库：
- ragas 依赖 OpenAI / LangChain，OpenAI 被你的 region 禁
- 三个核心指标自己实现 ~150 行，没必要拉 30+ 依赖

三指标定义（与 RAGAs 论文一致）：

1. **Faithfulness**：终稿陈述能从 retrieved papers 推出吗？
   - 拆陈述 → 每条对照 papers → 占比

2. **Answer Relevance**：终稿是否回答了原 query？
   - 反向生成：从答案能反推出 query 吗？余弦相似度

3. **Context Precision**：retrieved papers 中相关条目是否排在前？
   - 每篇 paper 标 relevant/irrelevant → MAP @ k

简化：用 LLM 直接打分（0.0-1.0），不做 chunk 拆分。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.llm_utils import chat_with_retry


FAITHFULNESS_PROMPT = """\
You are a strict fact-checker. Given a research draft and the source papers it claims to cite,
score whether the draft's claims can be supported by the papers.

Score 0.0–1.0:
- 1.0: Every numerical/factual claim is directly supported by paper abstracts.
- 0.5: Most claims supported, but 1-2 major claims unverifiable from papers.
- 0.0: Many claims fabricated or papers cited that don't support the claim.

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "unsupported_claims": [<str>, ...]}
"""

ANSWER_RELEVANCE_PROMPT = """\
You are an academic reviewer. Given the original research question and a final draft,
score whether the draft directly answers the question.

Score 0.0–1.0:
- 1.0: Draft directly addresses every aspect of the question.
- 0.5: Partially answers, some aspects missing or off-topic.
- 0.0: Draft mostly answers a different question.

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "missing_aspects": [<str>, ...]}
"""

CONTEXT_PRECISION_PROMPT = """\
You are evaluating retrieved papers for relevance to a research question.

For each paper (given as title + abstract), label "relevant" or "irrelevant" to the query.

Compute precision@k where k = number of retrieved papers, considering position
(top results matter more — use Mean Average Precision: MAP).

Output JSON: {"score": <float 0.0-1.0>, "labels": [{"arxiv_id": "...", "relevant": <bool>}, ...]}
"""


class RagasLiteEvaluator:
    """三指标评估器，DeepSeek-V4 当 judge。"""

    def __init__(
        self,
        llm_client: OpenAI,
        model: str = "deepseek/deepseek-v4-flash",
    ) -> None:
        self.llm = llm_client
        self.model = model

    def _judge_call(self, system: str, user: str) -> dict[str, Any]:
        content = chat_with_retry(
            self.llm,
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1500,
        )
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"score": 0.0, "reasoning": "parse error", "_raw": content}

    def faithfulness(self, draft: dict[str, Any]) -> dict[str, Any]:
        cites = draft.get("citations", [])
        raw_papers = draft.get("raw_papers", [])
        # raw_papers 字段保留了真实 abstract（researcher 注入）
        papers_str = "\n\n".join(
            f"[{p.get('arxiv_id', '?')}] {p.get('title', '')}\n"
            f"Abstract: {(p.get('abstract', '') or '')[:500]}"
            for p in raw_papers
        )
        draft_str = (
            f"Background:\n{draft.get('background', '')}\n\n"
            f"Methods:\n{draft.get('methods', '')}\n\n"
            f"Findings:\n{draft.get('findings', '')}"
        )
        user = f"=== Source papers ===\n{papers_str}\n\n=== Draft ===\n{draft_str}"
        return self._judge_call(FAITHFULNESS_PROMPT, user)

    def answer_relevance(self, query: str, draft: dict[str, Any]) -> dict[str, Any]:
        draft_str = (
            f"Background:\n{draft.get('background', '')}\n\n"
            f"Methods:\n{draft.get('methods', '')}\n\n"
            f"Findings:\n{draft.get('findings', '')}"
        )
        user = f"=== Original question ===\n{query}\n\n=== Draft ===\n{draft_str}"
        return self._judge_call(ANSWER_RELEVANCE_PROMPT, user)

    def context_precision(self, query: str, raw_papers: list[dict[str, Any]]) -> dict[str, Any]:
        papers_str = "\n\n".join(
            f"[{p.get('arxiv_id', '?')}] {p.get('title', '')}\n"
            f"Abstract: {(p.get('abstract', '') or '')[:300]}"
            for p in raw_papers
        )
        user = f"=== Query ===\n{query}\n\n=== Retrieved papers (in order) ===\n{papers_str}"
        return self._judge_call(CONTEXT_PRECISION_PROMPT, user)

    def evaluate_all(
        self,
        query: str,
        draft: dict[str, Any],
        raw_papers: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """跑三指标，返回综合报告。"""
        if raw_papers is None:
            raw_papers = draft.get("raw_papers", [])

        print("  [eval] Faithfulness ...")
        faith = self.faithfulness(draft)
        print(f"    {faith.get('score', '?')}")

        print("  [eval] Answer Relevance ...")
        relevance = self.answer_relevance(query, draft)
        print(f"    {relevance.get('score', '?')}")

        print("  [eval] Context Precision ...")
        precision = self.context_precision(query, raw_papers)
        print(f"    {precision.get('score', '?')}")

        avg = round(
            (
                float(faith.get("score", 0))
                + float(relevance.get("score", 0))
                + float(precision.get("score", 0))
            )
            / 3,
            3,
        )
        return {
            "faithfulness": faith,
            "answer_relevance": relevance,
            "context_precision": precision,
            "average": avg,
        }
