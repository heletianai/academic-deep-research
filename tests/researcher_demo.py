"""
Stage 1 Demo：Researcher Agent 单源（ArXiv）出初稿。

跑法：
  python -m tests.researcher_demo

输出：
  outputs/stage1_draft_<timestamp>.md
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# 让 import 找得到 src/
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.researcher import ResearcherAgent
from src.tools.arxiv_search import ArXivSearch


DEMO_QUERY = (
    "Multi-agent debate systems for reducing LLM hallucination "
    "and improving factual accuracy in academic research"
)


def main() -> None:
    load_dotenv(Path(__file__).parent.parent / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("OPENROUTER_API_KEY 未设置")

    print(f"[demo] 研究问题：{DEMO_QUERY}\n")

    # 初始化
    llm = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    arxiv_tool = ArXivSearch(top_k=5)
    researcher = ResearcherAgent(
        llm_client=llm,
        arxiv_tool=arxiv_tool,
        model="deepseek/deepseek-v4-flash",
        top_k=5,
    )

    # 跑
    print("[demo] 调用 ArXiv 检索 + LLM 综合 ...")
    draft = researcher.run(DEMO_QUERY)

    # 控制台打印摘要
    if "parse_error" in draft:
        print("[demo] LLM 输出 JSON 解析失败，原始内容：")
        print(draft.get("raw", "")[:500])
    else:
        print(f"[demo] ✓ 初稿生成完成")
        print(f"  - 背景：{len(draft.get('background', ''))} 字")
        print(f"  - 方法：{len(draft.get('methods', ''))} 字")
        print(f"  - 发现：{len(draft.get('findings', ''))} 字")
        print(f"  - 引用：{len(draft.get('citations', []))} 篇")

    # 落盘
    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    md_path = out_dir / f"stage1_draft_{ts}.md"
    md_path.write_text(researcher.render_markdown(draft), encoding="utf-8")
    print(f"\n[demo] markdown 初稿 → {md_path}")

    json_path = out_dir / f"stage1_draft_{ts}.json"
    json_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[demo] JSON 初稿     → {json_path}")

    # 引用真实性提示
    print("\n[demo] 引用真实性自检（前 3 篇）：")
    for c in draft.get("citations", [])[:3]:
        print(f"  [{c.get('arxiv_id', '?')}] {c.get('title', '?')[:60]}")
        print(f"      {c.get('url', '?')}")


if __name__ == "__main__":
    main()
