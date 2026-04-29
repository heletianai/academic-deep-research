"""
辩论主流程：Researcher → 红蓝对抗循环 → Judge 终审 → 终稿。

Stage 2 baseline 用裸循环（不上 LangGraph，节省 dependency；Stage 3 可换成 LangGraph）。
"""

from __future__ import annotations

import json
from typing import Any

from src.agents.critic import CriticAgent
from src.agents.defender import DefenderAgent
from src.agents.judge import JudgeAgent
from src.agents.researcher import ResearcherAgent


def _draft_to_text(draft: dict[str, Any]) -> str:
    """把 dict draft 序列化成 markdown 风格文本，供 Critic / Defender / Judge 读。"""
    bg = draft.get("background", "")
    methods = draft.get("methods", "")
    findings = draft.get("findings", "")
    cites = draft.get("citations", [])
    cite_lines = "\n".join(
        f"- [{c.get('arxiv_id', '?')}] {c.get('title', '?')}" for c in cites
    )
    return (
        "## Background\n\n" + bg + "\n\n"
        "## Methods\n\n" + methods + "\n\n"
        "## Findings\n\n" + findings + "\n\n"
        "## Citations\n\n" + cite_lines
    )


def run_pipeline(
    query: str,
    researcher: ResearcherAgent,
    critic: CriticAgent,
    defender: DefenderAgent,
    judge: JudgeAgent,
    max_rounds: int = 2,
    verbose: bool = True,
    evaluator: Any = None,
) -> dict[str, Any]:
    """
    端到端辩论 pipeline。

    流程：
        Stage 1: researcher.run(query) → draft0
        Stage 2 循环（最多 max_rounds 轮）：
            critic.run(draft) → critique
            if critique 全空 → break
            defender.run(draft, critique) → defense
            draft = defender.apply_revisions(draft, defense)
        Stage 2 终审: judge.run(final_draft, debate_history)

    Returns:
        {
            "query": str,
            "draft0": dict,                      # 原始初稿
            "final_draft": dict,                 # 经过辩论修正后的终稿
            "debate_history": [{"critique","defense"}, ...],
            "verdict": dict,                     # judge 输出
            "rounds_used": int,
        }
    """
    if verbose:
        print(f"\n[pipeline] Stage 1 — Researcher 生成初稿 ...")
    draft = researcher.run(query)
    draft0 = json.loads(json.dumps(draft, ensure_ascii=False))  # deep copy via JSON
    debate_history: list[dict[str, Any]] = []

    if "parse_error" in draft:
        if verbose:
            print("[pipeline] ✗ Researcher JSON 解析失败，pipeline 中止")
        return {
            "query": query,
            "draft0": draft0,
            "final_draft": draft,
            "debate_history": [],
            "verdict": {"verdict": "REJECT", "reasoning": "Stage 1 解析失败"},
            "rounds_used": 0,
        }

    rounds_used = 0
    for r in range(1, max_rounds + 1):
        if verbose:
            print(f"\n[pipeline] Stage 2 — Round {r}/{max_rounds} 红蓝对抗")

        if verbose:
            print(f"  [Critic] 三维质疑 ...")
        draft_text = _draft_to_text(draft)
        critique = critic.run(draft_text, round_num=r)

        n_critiques = sum(len(critique.get(d, [])) for d in ("factual", "logical", "citation"))
        if verbose:
            print(
                f"    factual: {len(critique.get('factual', []))}, "
                f"logical: {len(critique.get('logical', []))}, "
                f"citation: {len(critique.get('citation', []))}  (总 {n_critiques})"
            )

        if CriticAgent.is_empty(critique):
            if verbose:
                print("  [Critic] 无质疑，提前终止辩论")
            debate_history.append({"critique": critique, "defense": None, "round": r})
            break

        if verbose:
            print(f"  [Defender] 先搜再答 ...")
        defense = defender.run(draft_text, critique, round_num=r)
        n_rebut = sum(1 for x in defense.get("responses", []) if x.get("stance") == "REBUT")
        n_concede = sum(1 for x in defense.get("responses", []) if x.get("stance") == "CONCEDE")
        if verbose:
            print(
                f"    REBUT: {n_rebut}, CONCEDE: {n_concede}, "
                f"新检索 paper: {len(defense.get('evidence_papers', []))}"
            )

        debate_history.append({"critique": critique, "defense": defense, "round": r})
        rounds_used = r

        # 应用修正
        draft = defender.apply_revisions(draft, defense)

    # Stage 2 终审
    if verbose:
        print(f"\n[pipeline] Stage 2 — Judge 终审")
    final_text = _draft_to_text(draft)
    verdict = judge.run(final_text, debate_history)
    if verbose:
        scores = verdict.get("scores", {})
        print(
            f"  [Judge] verdict={verdict.get('verdict')} "
            f"avg={verdict.get('average')} "
            f"(factual={scores.get('factual')}, logical={scores.get('logical')}, "
            f"citation={scores.get('citation')})"
        )

    result = {
        "query": query,
        "draft0": draft0,
        "final_draft": draft,
        "debate_history": debate_history,
        "verdict": verdict,
        "rounds_used": rounds_used,
    }

    # Stage 3: 可选 RAGAs-lite 评估
    if evaluator is not None:
        if verbose:
            print(f"\n[pipeline] Stage 3 — RAGAs-lite 三指标评估")
        eval_report = evaluator.evaluate_all(
            query=query,
            draft=draft,
            raw_papers=draft.get("raw_papers", []),
        )
        result["eval"] = eval_report
        if verbose:
            print(
                f"  [eval] avg={eval_report['average']} "
                f"(faith={eval_report['faithfulness'].get('score', '?')}, "
                f"rel={eval_report['answer_relevance'].get('score', '?')}, "
                f"prec={eval_report['context_precision'].get('score', '?')})"
            )

    return result
