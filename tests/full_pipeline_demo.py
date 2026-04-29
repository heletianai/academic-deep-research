"""
Stage 3 Demo：多源（ArXiv + Semantic Scholar）+ 红蓝对抗 + RAGAs-lite 评估。

跑法：
  python -m tests.full_pipeline_demo

输出（落盘到 outputs/）：
  - full_pipeline_<ts>.md   人类可读的辩论 + 评估全程报告
  - full_pipeline_<ts>.json 完整结构化 dump
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
from src.eval.ragas_lite import RagasLiteEvaluator
from src.graph import run_pipeline
from src.tools.arxiv_search import ArXivSearch
from src.tools.semantic_scholar import MultiSourceSearch, SemanticScholarSearch


DEMO_QUERY = (
    "Multi-agent debate systems for reducing LLM hallucination "
    "and improving factual accuracy in academic research"
)


def render_markdown(result: dict) -> str:
    out: list[str] = []
    out.append("# Full Pipeline 报告（多源 + 红蓝对抗 + RAGAs-lite）\n")
    out.append(f"**Query**: {result['query']}\n")
    out.append(f"**Rounds used**: {result['rounds_used']}\n")
    verdict = result["verdict"]
    out.append(
        f"**Verdict**: **{verdict.get('verdict', '?')}** "
        f"(avg={verdict.get('average', '?')})\n"
    )

    # Stage 3 eval 报告
    if "eval" in result:
        e = result["eval"]
        out.append(f"\n## RAGAs-lite 三指标\n")
        out.append(f"- **Faithfulness**: {e['faithfulness'].get('score', '?')} — {e['faithfulness'].get('reasoning', '')[:200]}")
        out.append(f"- **Answer Relevance**: {e['answer_relevance'].get('score', '?')} — {e['answer_relevance'].get('reasoning', '')[:200]}")
        out.append(f"- **Context Precision**: {e['context_precision'].get('score', '?')}")
        out.append(f"- **平均分**: {e.get('average', '?')}")

    out.append("\n---\n")
    out.append("\n## 数据来源分布\n")
    raw_papers = result.get("draft0", {}).get("raw_papers", [])
    by_src: dict[str, int] = {}
    for p in raw_papers:
        by_src[p.get("source", "unknown")] = by_src.get(p.get("source", "unknown"), 0) + 1
    for src, n in by_src.items():
        out.append(f"- {src}: {n} 篇")

    out.append("\n---\n")
    out.append("\n## Stage 1 初稿\n")
    d0 = result["draft0"]
    out.append(f"### 背景\n\n{d0.get('background', '')}\n")
    out.append(f"### 方法\n\n{d0.get('methods', '')}\n")
    out.append(f"### 发现\n\n{d0.get('findings', '')}\n")

    out.append("\n---\n")
    out.append("\n## Stage 2 辩论摘要\n")
    for h in result["debate_history"]:
        r = h.get("round", "?")
        c = h.get("critique", {})
        d = h.get("defense") or {}
        n_critiques = sum(len(c.get(d_, [])) for d_ in ("factual", "logical", "citation"))
        n_responses = len(d.get("responses", []))
        n_concede = sum(1 for x in d.get("responses", []) if x.get("stance") == "CONCEDE")
        out.append(f"\n### Round {r}: {n_critiques} 条质疑 → {n_responses} 回应（{n_concede} CONCEDE）")

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
    arxiv_tool = ArXivSearch(top_k=3)
    ss_tool = SemanticScholarSearch(top_k=3)
    multi_search = MultiSourceSearch(arxiv_tool=arxiv_tool, ss_tool=ss_tool, top_k=5)

    researcher = ResearcherAgent(llm_client=llm, arxiv_tool=multi_search, top_k=5)
    critic = CriticAgent(llm_client=llm)
    defender = DefenderAgent(llm_client=llm, arxiv_tool=arxiv_tool, search_per_critique=2)
    judge = JudgeAgent(llm_client=llm)
    evaluator = RagasLiteEvaluator(llm_client=llm)

    result = run_pipeline(
        query=DEMO_QUERY,
        researcher=researcher,
        critic=critic,
        defender=defender,
        judge=judge,
        max_rounds=2,
        verbose=True,
        evaluator=evaluator,
    )

    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path = out_dir / f"full_pipeline_{ts}.md"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    print(f"\n[demo] markdown 报告 → {md_path}")

    json_path = out_dir / f"full_pipeline_{ts}.json"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[demo] JSON dump     → {json_path}")


if __name__ == "__main__":
    main()
