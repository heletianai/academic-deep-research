"""
项目 2 Ablation 主脚本：5 配置 × 10 topic × N seed → JSON。

跑法：
    # 完整 5×10×3 = 150 次
    python -m scripts.run_ablation

    # 子集（调试用）
    python -m scripts.run_ablation --topics T01,T02 --configs baseline,full --seeds 1

    # 后台跑（推荐）
    nohup python -m scripts.run_ablation > /tmp/ablation.log 2>&1 &

输出：
    benchmarks/results/ablation_<timestamp>.json   完整结构化数据
    benchmarks/results/ablation_<timestamp>.md     人类可读摘要

设计：
- 每次 pipeline 调用都用 4 维 QualityEvaluator 评分
- 失败的 run 标 status="error" 但不中断整个 ablation
- 每跑完 5 次刷一次中间 JSON（防崩溃丢全部数据）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.critic import CriticAgent
from src.agents.defender import DefenderAgent
from src.agents.judge import JudgeAgent
from src.agents.researcher import ResearcherAgent
from src.eval.quality_evaluator import QualityEvaluator
from src.graph import run_pipeline
from src.tools.arxiv_search import ArXivSearch
from src.tools.semantic_scholar import MultiSourceSearch, SemanticScholarSearch


def load_config() -> dict[str, Any]:
    cfg_path = ROOT / "configs" / "eval_topics.yaml"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def make_pipeline(llm: OpenAI, config: dict[str, Any], model: str) -> dict[str, Any]:
    """根据 ablation 配置构造 pipeline 组件。"""
    if config["multisource"]:
        search_tool = MultiSourceSearch(
            arxiv_tool=ArXivSearch(top_k=3),
            ss_tool=SemanticScholarSearch(top_k=3),
            top_k=5,
        )
    else:
        search_tool = ArXivSearch(top_k=5)

    researcher = ResearcherAgent(llm_client=llm, arxiv_tool=search_tool, model=model, top_k=5)
    critic = CriticAgent(llm_client=llm, model=model)
    defender = DefenderAgent(
        llm_client=llm, arxiv_tool=ArXivSearch(top_k=3), model=model, search_per_critique=0
    )
    judge = JudgeAgent(llm_client=llm, model=model)
    return {"researcher": researcher, "critic": critic, "defender": defender, "judge": judge}


def run_one(
    llm: OpenAI,
    topic: dict[str, Any],
    config: dict[str, Any],
    seed: int,
    evaluator: QualityEvaluator,
    model: str,
) -> dict[str, Any]:
    """跑一次 pipeline + 4 维评估。"""
    t0 = time.time()
    components = make_pipeline(llm, config, model)

    try:
        # 注意：pipeline 内部已包含 evaluator=None 的 baseline 路径，但我们单独跑 evaluator
        result = run_pipeline(
            query=topic["query"],
            researcher=components["researcher"],
            critic=components["critic"],
            defender=components["defender"],
            judge=components["judge"],
            max_rounds=config["max_rounds"],
            verbose=False,
            evaluator=None,  # 我们用新的 4 维 evaluator 单独评
        )

        # 用 4 维 QualityEvaluator 评 final_draft
        eval_report = evaluator.evaluate_all(
            query=topic["query"],
            draft=result["final_draft"],
            verbose=False,
        )

        elapsed = time.time() - t0
        return {
            "topic_id": topic["id"],
            "topic_query": topic["query"],
            "domain": topic["domain"],
            "config": config["name"],
            "seed": seed,
            "rounds_used": result["rounds_used"],
            "verdict": result["verdict"].get("verdict"),
            "verdict_avg": result["verdict"].get("average"),
            "scores": eval_report["scores"],
            "weighted_average": eval_report["weighted_average"],
            "elapsed_sec": round(elapsed, 1),
            "n_papers": len(result["draft0"].get("raw_papers", [])),
            "n_citations": len(result["final_draft"].get("citations", [])),
            "status": "ok",
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "topic_id": topic["id"],
            "topic_query": topic["query"],
            "domain": topic["domain"],
            "config": config["name"],
            "seed": seed,
            "elapsed_sec": round(elapsed, 1),
            "status": "error",
            "error": str(e)[:300],
            "traceback": traceback.format_exc()[:1000],
        }


def load_existing_records(out_dir: Path) -> list[dict[str, Any]]:
    """从 out_dir 下所有 ablation_*.json 加载已跑成功的 records，去重。"""
    seen: set[tuple[str, str, int]] = set()
    records: list[dict[str, Any]] = []
    for path in sorted(out_dir.glob("ablation_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            recs = data.get("records", []) if isinstance(data, dict) else data
            for r in recs:
                if r.get("status") != "ok":
                    continue
                key = (r.get("config", ""), r.get("topic_id", ""), r.get("seed", 0))
                if key in seen:
                    continue
                seen.add(key)
                records.append(r)
        except (OSError, json.JSONDecodeError):
            continue
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics", type=str, default=None, help="逗号分隔 topic id 子集，如 T01,T02")
    parser.add_argument("--configs", type=str, default=None, help="逗号分隔 config 子集，如 baseline,full")
    parser.add_argument("--seeds", type=int, default=None, help="覆盖 yaml 的 seeds_per_run")
    parser.add_argument("--out-dir", type=str, default=None, help="输出目录（默认 benchmarks/results/）")
    parser.add_argument("--resume", action="store_true", help="跳过已跑成功的 (config, topic, seed) 组合")
    parser.add_argument("--inter-sleep", type=float, default=3.0, help="每条 pipeline 之间 sleep 秒数（避让 ArXiv 429）— 仅串行模式生效")
    parser.add_argument("--workers", type=int, default=3, help="并发线程数（默认 3，设 1 退化串行）")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    # Provider 切换：zhipu (默认免费) / openrouter
    provider = os.getenv("LLM_PROVIDER", "zhipu").lower()
    if provider == "zhipu":
        api_key = os.getenv("ZHIPU_API_KEY")
        if not api_key:
            sys.exit("ZHIPU_API_KEY 未设置（在 .env）")
        base_url = "https://open.bigmodel.cn/api/paas/v4"
        model = "glm-4-flash"
        print(f"[ablation] provider=zhipu model={model} (free tier)")
    elif provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            sys.exit("OPENROUTER_API_KEY 未设置（在 .env）")
        base_url = "https://openrouter.ai/api/v1"
        model = "deepseek/deepseek-v4-flash"
        print(f"[ablation] provider=openrouter model={model}")
    elif provider == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            sys.exit("DEEPSEEK_API_KEY 未设置（在 .env）")
        base_url = "https://api.deepseek.com/v1"
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        print(f"[ablation] provider=deepseek model={model} (paid, cache-friendly)")
    else:
        sys.exit(f"未知 LLM_PROVIDER: {provider}")

    cfg = load_config()
    topics = cfg["topics"]
    configs = cfg["configs"]
    seeds_per_run = args.seeds or cfg["seeds_per_run"]

    # 子集过滤
    if args.topics:
        wanted = set(args.topics.split(","))
        topics = [t for t in topics if t["id"] in wanted]
    if args.configs:
        wanted = set(args.configs.split(","))
        configs = [c for c in configs if c["name"] in wanted]

    total = len(topics) * len(configs) * seeds_per_run
    print(f"[ablation] {len(topics)} topic × {len(configs)} config × {seeds_per_run} seed = {total} 次 pipeline")

    llm = OpenAI(api_key=api_key, base_url=base_url)
    evaluator = QualityEvaluator(llm_client=llm, model=model)

    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "benchmarks" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"ablation_{ts}.json"

    # Resume: 加载所有历史 ok records，跳过已跑组合
    skip_set: set[tuple[str, str, int]] = set()
    results: list[dict[str, Any]] = []
    if args.resume:
        existing = load_existing_records(out_dir)
        for r in existing:
            skip_set.add((r["config"], r["topic_id"], r["seed"]))
        results.extend(existing)
        print(f"[ablation] --resume 加载已跑成功 {len(existing)} 条，跳过这些组合")

    t_start = time.time()

    # 展开任务列表（跳过 resume skip_set）
    tasks: list[tuple[dict[str, Any], dict[str, Any], int]] = []
    for config in configs:
        for topic in topics:
            for s in range(1, seeds_per_run + 1):
                key = (config["name"], topic["id"], s)
                if key in skip_set:
                    continue
                tasks.append((config, topic, s))

    print(f"[ablation] 待跑 {len(tasks)} 条 / 并发 workers={args.workers}")

    results_lock = threading.Lock()
    completed_count = 0

    def worker(task: tuple[dict[str, Any], dict[str, Any], int]) -> dict[str, Any]:
        config, topic, seed = task
        return run_one(llm, topic, config, seed, evaluator, model)

    if args.workers <= 1:
        # 串行回退路径（保留 inter-sleep 节流）
        for ti, task in enumerate(tasks, 1):
            rec = worker(task)
            results.append(rec)
            completed_count += 1
            idx = len(results)
            cfg_n, top_id, seed_n = task[0]["name"], task[1]["id"], task[2]
            if rec["status"] == "ok":
                print(
                    f"[{idx}/{total}] config={cfg_n} | topic={top_id} | seed={seed_n} ... "
                    f"avg={rec['weighted_average']} "
                    f"(F={rec['scores']['faithfulness']:.2f} "
                    f"C={rec['scores']['coverage']:.2f} "
                    f"CA={rec['scores']['citation_accuracy']:.2f} "
                    f"S={rec['scores']['structure_coherence']:.2f}) "
                    f"{rec['elapsed_sec']}s",
                    flush=True,
                )
            else:
                print(
                    f"[{idx}/{total}] config={cfg_n} | topic={top_id} | seed={seed_n} ... "
                    f"ERROR: {rec.get('error', '')[:80]}",
                    flush=True,
                )
            if args.inter_sleep > 0:
                time.sleep(args.inter_sleep)
            if completed_count % 5 == 0:
                json_path.write_text(
                    json.dumps(
                        {"meta": {"total": total, "done": idx, "ts": ts}, "records": results},
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
    else:
        # 并发路径
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {executor.submit(worker, t): t for t in tasks}
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                cfg_n, top_id, seed_n = task[0]["name"], task[1]["id"], task[2]
                try:
                    rec = future.result()
                except Exception as e:  # 兜底：worker 自身 try/except 已经包了，这里不应该到
                    rec = {
                        "topic_id": top_id,
                        "topic_query": task[1]["query"],
                        "domain": task[1]["domain"],
                        "config": cfg_n,
                        "seed": seed_n,
                        "elapsed_sec": 0.0,
                        "status": "error",
                        "error": f"worker uncaught: {str(e)[:200]}",
                        "traceback": traceback.format_exc()[:1000],
                    }

                with results_lock:
                    results.append(rec)
                    completed_count += 1
                    idx = len(results)
                    if rec["status"] == "ok":
                        print(
                            f"[{idx}/{total}] config={cfg_n} | topic={top_id} | seed={seed_n} ... "
                            f"avg={rec['weighted_average']} "
                            f"(F={rec['scores']['faithfulness']:.2f} "
                            f"C={rec['scores']['coverage']:.2f} "
                            f"CA={rec['scores']['citation_accuracy']:.2f} "
                            f"S={rec['scores']['structure_coherence']:.2f}) "
                            f"{rec['elapsed_sec']}s",
                            flush=True,
                        )
                    else:
                        print(
                            f"[{idx}/{total}] config={cfg_n} | topic={top_id} | seed={seed_n} ... "
                            f"ERROR: {rec.get('error', '')[:80]}",
                            flush=True,
                        )
                    if completed_count % 5 == 0:
                        json_path.write_text(
                            json.dumps(
                                {"meta": {"total": total, "done": idx, "ts": ts}, "records": results},
                                ensure_ascii=False,
                                indent=2,
                            ),
                            encoding="utf-8",
                        )

    elapsed_total = time.time() - t_start
    print(f"\n[ablation] 全部完成，{len(results)} 条 / 用时 {elapsed_total / 60:.1f} 分钟")

    # 最终落盘
    final = {
        "meta": {
            "total": total,
            "done": len(results),
            "ts": ts,
            "elapsed_sec": round(elapsed_total, 1),
            "n_topics": len(topics),
            "n_configs": len(configs),
            "seeds": seeds_per_run,
            "ok": sum(1 for r in results if r["status"] == "ok"),
            "error": sum(1 for r in results if r["status"] == "error"),
        },
        "records": results,
    }
    json_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ablation] JSON  → {json_path}")


if __name__ == "__main__":
    main()
