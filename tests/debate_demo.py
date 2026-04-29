"""
Stage 2 Demo：Researcher → Critic ↔ Defender 辩论 → Judge 终审。

跑法：
  python -m tests.debate_demo

输出（落盘到 outputs/）：
  - debate_<ts>.md   人类可读的辩论全程报告
  - debate_<ts>.json 完整结构化 dump
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.critic import CriticAgent
from src.agents.defender import DefenderAgent
from src.agents.judge import JudgeAgent
from src.agents.researcher import ResearcherAgent
from src.graph import run_pipeline
from src.tools.arxiv_search import ArXivSearch


DEMO_QUERY = (
    "Multi-agent debate systems for reducing LLM hallucination "
    "and improving factual accuracy in academic research"
)


def render_markdown(result: dict) -> str:
    """把 pipeline 全程渲染成 markdown 报告。"""
    out: list[str] = []
    out.append(f"# 红蓝对抗辩论报告\n")
    out.append(f"**Query**: {result['query']}\n")
    out.append(f"**Rounds used**: {result['rounds_used']}\n")
    verdict = result["verdict"]
    out.append(
        f"**Verdict**: **{verdict.get('verdict', '?')}** "
        f"(avg={verdict.get('average', '?')})\n"
    )
    scores = verdict.get("scores", {})
    out.append(
        f"- Factual: {scores.get('factual', '?')}\n"
        f"- Logical: {scores.get('logical', '?')}\n"
        f"- Citation: {scores.get('citation', '?')}\n"
    )
    out.append(f"\n**Reasoning**: {verdict.get('reasoning', '')}\n")
    out.append("\n---\n")

    out.append("\n## Stage 1 初稿\n")
    d0 = result["draft0"]
    out.append(f"### 背景\n\n{d0.get('background', '')}\n")
    out.append(f"### 方法\n\n{d0.get('methods', '')}\n")
    out.append(f"### 发现\n\n{d0.get('findings', '')}\n")

    out.append("\n---\n")
    out.append("\n## Stage 2 辩论全程\n")
    for h in result["debate_history"]:
        r = h.get("round", "?")
        c = h.get("critique", {})
        d = h.get("defense") or {}
        out.append(f"\n### Round {r}\n")
        out.append("**Critic 三维质疑**：\n")
        for dim_name, dim_zh in (("factual", "事实"), ("logical", "逻辑"), ("citation", "引用")):
            items = c.get(dim_name, [])
            if items:
                out.append(f"- **{dim_zh}**：")
                for q in items:
                    out.append(f"  - {q}")

        if d:
            out.append("\n**Defender 回应**：\n")
            for r_item in d.get("responses", []):
                stance = r_item.get("stance", "?")
                content = r_item.get("content", "")
                cites = r_item.get("citations", [])
                out.append(f"- [{stance}] {content}")
                if cites:
                    out.append(f"  - refs: {cites}")
            conceded = d.get("conceded_points", [])
            if conceded:
                out.append(f"\n**Defender 已承认修正**: {conceded}")

    out.append("\n---\n")
    out.append("\n## Stage 2 终稿\n")
    fd = result["final_draft"]
    out.append(f"### 背景\n\n{fd.get('background', '')}\n")
    out.append(f"### 方法\n\n{fd.get('methods', '')}\n")
    out.append(f"### 发现\n\n{fd.get('findings', '')}\n")
    out.append(f"### 引用\n")
    for c in fd.get("citations", []):
        out.append(f"- [{c.get('arxiv_id', '?')}] {c.get('title', '?')} — {c.get('url', '')}")
    return "\n".join(out)


def main() -> None:
    load_dotenv(Path(__file__).parent.parent / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("OPENROUTER_API_KEY 未设置")

    print(f"[demo] 研究问题：{DEMO_QUERY}")

    llm = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    arxiv_tool = ArXivSearch(top_k=5)

    researcher = ResearcherAgent(llm_client=llm, arxiv_tool=arxiv_tool, top_k=5)
    critic = CriticAgent(llm_client=llm)
    defender = DefenderAgent(llm_client=llm, arxiv_tool=arxiv_tool, search_per_critique=2)
    judge = JudgeAgent(llm_client=llm)

    result = run_pipeline(
        query=DEMO_QUERY,
        researcher=researcher,
        critic=critic,
        defender=defender,
        judge=judge,
        max_rounds=2,
        verbose=True,
    )

    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path = out_dir / f"debate_{ts}.md"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"\n[demo] markdown 报告 → {md_path}")

    json_path = out_dir / f"debate_{ts}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[demo] JSON dump     → {json_path}")


if __name__ == "__main__":
    main()
