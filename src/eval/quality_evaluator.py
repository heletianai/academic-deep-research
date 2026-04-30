"""
4 维 Quality Evaluator（项目 2 升级版）：在 RAGAs-lite 三指标基础上扩展为 4 维。

新增 vs ragas_lite.py：
- 复用 Faithfulness（事实性）、Coverage（原 Answer Relevance 改名，更贴近 research review 语义）
- 新增 Citation Accuracy：验证 arxiv_id 真实性 + 引用与陈述匹配度
- 新增 Structure Coherence：章节衔接 + 论证完整度
- 综合分数：加权平均（默认 4 维等权 0.25）

设计动机：
- 学术研究综述质量不止 RAG 三指标，论文引用真实性 + 文档结构是 hallmark
- Citation Accuracy 抓引用幻觉（项目 2 的核心问题）
- Structure Coherence 抓"东拼西凑"问题（多 Researcher 并行的常见 bug）
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.llm_utils import chat_with_retry


FAITHFULNESS_PROMPT = """\
You are a strict fact-checker. Given a research draft and the source papers it cites,
score whether the draft's claims can be supported by the papers.

Score 0.0–1.0:
- 1.0: Every numerical/factual claim is directly supported by paper abstracts.
- 0.5: Most claims supported, but 1-2 major claims unverifiable from papers.
- 0.0: Many claims fabricated or papers cited that don't support the claim.

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "unsupported_claims": [<str>, ...]}
"""

COVERAGE_PROMPT = """\
You are an academic reviewer evaluating research survey coverage. Given a research question
and the final draft, score how comprehensively the draft addresses the question's key sub-aspects.

Coverage = breadth (does it touch all major sub-topics?) + depth (does each sub-topic get
substantive treatment, not just one sentence?).

Score 0.0–1.0:
- 1.0: Draft covers ≥ 4 distinct sub-aspects of the question, each with depth.
- 0.7: Covers 2-3 sub-aspects with reasonable depth, or 4+ but one is shallow.
- 0.4: Covers 1-2 sub-aspects, mostly surface-level treatment.
- 0.0: Draft mostly answers a different question or has no real depth.

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "covered_aspects": [<str>, ...], "missing_aspects": [<str>, ...]}
"""

CITATION_ACCURACY_PROMPT = """\
You are a citation auditor. For each citation in the draft, verify two things:
1. Does the cited arxiv_id appear in the source papers list?
2. Does the citation actually support the claim it's attached to?

Compute a precision-style score:
- Numerator: # citations where arxiv_id is in source list AND supports its claim
- Denominator: # total citations in the draft

Score 0.0–1.0 (= numerator / denominator), rounded to 2 decimals.

Common failures to flag:
- Citing arxiv_id NOT in source list (fabricated citation)
- Citing real paper but for unrelated claim ("paper X says Y" when paper X is about Z)
- Missing citations for major claims that need them

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "fabricated_ids": [<str>, ...], "misattributed": [<str>, ...]}
"""

STRUCTURE_COHERENCE_PROMPT = """\
You are evaluating the structural coherence of a research draft. The draft has three sections:
Background, Methods, Findings. Score how well they flow together.

Look for:
1. Background → Methods transition: do methods actually address questions raised in background?
2. Methods → Findings transition: are findings derived from the methods discussed?
3. Internal consistency within each section (no contradictions)
4. Logical ordering (general → specific within each section)

Score 0.0–1.0:
- 1.0: All transitions natural, no contradictions, logical flow.
- 0.7: One weak transition or one minor contradiction.
- 0.4: Sections feel disconnected (e.g., Methods discusses X but Findings about Y).
- 0.0: Sections are essentially unrelated paragraphs stitched together.

Output JSON: {"score": <float>, "reasoning": "<2-3 sentences>", "issues": [<str>, ...]}
"""


class QualityEvaluator:
    """4 维 Quality Evaluator: Faithfulness / Coverage / Citation Accuracy / Structure Coherence."""

    DEFAULT_WEIGHTS = {
        "faithfulness": 0.30,
        "coverage": 0.25,
        "citation_accuracy": 0.25,
        "structure_coherence": 0.20,
    }

    def __init__(
        self,
        llm_client: OpenAI,
        model: str = "deepseek/deepseek-v4-flash",
        weights: dict[str, float] | None = None,
    ) -> None:
        self.llm = llm_client
        self.model = model
        self.weights = weights or self.DEFAULT_WEIGHTS

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

    @staticmethod
    def _draft_str(draft: dict[str, Any]) -> str:
        return (
            f"Background:\n{draft.get('background', '')}\n\n"
            f"Methods:\n{draft.get('methods', '')}\n\n"
            f"Findings:\n{draft.get('findings', '')}"
        )

    @staticmethod
    def _papers_str(raw_papers: list[dict[str, Any]], abstract_chars: int = 500) -> str:
        return "\n\n".join(
            f"[{p.get('arxiv_id', '?')}] {p.get('title', '')}\n"
            f"Abstract: {(p.get('abstract', '') or '')[:abstract_chars]}"
            for p in raw_papers
        )

    def faithfulness(self, draft: dict[str, Any]) -> dict[str, Any]:
        raw_papers = draft.get("raw_papers", [])
        user = (
            f"=== Source papers ===\n{self._papers_str(raw_papers)}\n\n"
            f"=== Draft ===\n{self._draft_str(draft)}"
        )
        return self._judge_call(FAITHFULNESS_PROMPT, user)

    def coverage(self, query: str, draft: dict[str, Any]) -> dict[str, Any]:
        user = (
            f"=== Original research question ===\n{query}\n\n"
            f"=== Draft ===\n{self._draft_str(draft)}"
        )
        return self._judge_call(COVERAGE_PROMPT, user)

    def citation_accuracy(self, draft: dict[str, Any]) -> dict[str, Any]:
        raw_papers = draft.get("raw_papers", [])
        valid_ids = sorted({p.get("arxiv_id", "") for p in raw_papers if p.get("arxiv_id")})
        cites = draft.get("citations", [])
        cite_lines = "\n".join(
            f"- [{c.get('arxiv_id', '?')}] {c.get('title', '')}" for c in cites
        )
        user = (
            f"=== Valid arxiv_ids (from source papers) ===\n{', '.join(valid_ids)}\n\n"
            f"=== Source papers ===\n{self._papers_str(raw_papers, abstract_chars=300)}\n\n"
            f"=== Draft ===\n{self._draft_str(draft)}\n\n"
            f"=== Citations declared in draft ===\n{cite_lines}"
        )
        return self._judge_call(CITATION_ACCURACY_PROMPT, user)

    def structure_coherence(self, draft: dict[str, Any]) -> dict[str, Any]:
        user = f"=== Draft ===\n{self._draft_str(draft)}"
        return self._judge_call(STRUCTURE_COHERENCE_PROMPT, user)

    def evaluate_all(
        self,
        query: str,
        draft: dict[str, Any],
        verbose: bool = True,
    ) -> dict[str, Any]:
        """跑 4 维评估，返回综合报告。"""
        if verbose:
            print("  [eval] Faithfulness ...")
        faith = self.faithfulness(draft)
        if verbose:
            print(f"    {faith.get('score', '?')}")

        if verbose:
            print("  [eval] Coverage ...")
        cov = self.coverage(query, draft)
        if verbose:
            print(f"    {cov.get('score', '?')}")

        if verbose:
            print("  [eval] Citation Accuracy ...")
        cite_acc = self.citation_accuracy(draft)
        if verbose:
            print(f"    {cite_acc.get('score', '?')}")

        if verbose:
            print("  [eval] Structure Coherence ...")
        struct = self.structure_coherence(draft)
        if verbose:
            print(f"    {struct.get('score', '?')}")

        scores = {
            "faithfulness": float(faith.get("score", 0)),
            "coverage": float(cov.get("score", 0)),
            "citation_accuracy": float(cite_acc.get("score", 0)),
            "structure_coherence": float(struct.get("score", 0)),
        }
        weighted_avg = round(
            sum(scores[k] * self.weights[k] for k in scores), 3
        )
        return {
            "faithfulness": faith,
            "coverage": cov,
            "citation_accuracy": cite_acc,
            "structure_coherence": struct,
            "scores": scores,
            "weights": self.weights,
            "weighted_average": weighted_avg,
        }
