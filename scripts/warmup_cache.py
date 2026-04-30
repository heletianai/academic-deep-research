"""
ArXiv papers 缓存预热：跑 10 topic × {top_k=5, top_k=3} 直接打 ArXiv API 写 cache。

用途：
- v5 ablation 跑 debate/full 时撞 ArXiv IP 限速，T02-T10 的 query|5 没成功
- IP 解封后跑这个脚本预热 cache，让 --resume 重跑时 Researcher 阶段 cache hit
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.tools.arxiv_search import ArXivSearch


def main() -> None:
    cfg = yaml.safe_load((ROOT / "configs" / "eval_topics.yaml").read_text(encoding="utf-8"))
    topics = cfg["topics"]

    # 只 warm Researcher 用的 top_k=5（Defender 的 top_k=3 是 LLM 生成的动态 critique query，预热 topic query 没用）
    for top_k in (5,):
        tool = ArXivSearch(top_k=top_k)
        for t in topics:
            q = t["query"]
            cache_path = tool._cache_key(q, top_k)
            if cache_path.exists():
                print(f"[warmup] {t['id']} top_k={top_k} → cached, skip")
                continue
            print(f"[warmup] {t['id']} top_k={top_k} → fetching ...", end=" ", flush=True)
            t0 = time.time()
            try:
                results = tool.search(q, top_k=top_k)
                print(f"got {len(results)} in {time.time() - t0:.1f}s")
            except Exception as e:
                print(f"ERR: {e}")
            time.sleep(15.0)  # 拉到 15s 间隔，避免连发触发 ArXiv IP 限速

    print("\n[warmup] done")


if __name__ == "__main__":
    main()
