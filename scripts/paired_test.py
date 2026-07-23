"""Paired significance test: each config vs baseline on (topic_id, seed) pairs.

Bootstrap 95% CI on paired score differences — the honest upgrade over
mean-vs-mean tables (controls topic/seed variance). Zero API cost.

Usage: python scripts/paired_test.py [path/to/ablation.json]
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

DIMENSIONS = ["faithfulness", "coverage", "citation_accuracy", "structure_coherence"]
N_BOOT = 10000
SEED = 42


def boot_ci(diffs, n=N_BOOT):
    rng = random.Random(SEED)
    means = sorted(
        sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n)
    )
    return means[int(0.025 * n)], means[int(0.975 * n)]


def main(path):
    data = json.loads(Path(path).read_text())
    recs = [r for r in data["records"] if r.get("status") == "ok"]
    base = {(r["topic_id"], r["seed"]): r for r in recs if r["config"] == "baseline"}
    configs = sorted({r["config"] for r in recs} - {"baseline"})

    print(f"# Paired significance vs baseline\n")
    print(f"Source: `{path}` — {len(recs)} ok records, "
          f"configs: {dict(Counter(r['config'] for r in recs))}\n")
    print("Positive delta = better than baseline. CI excluding 0 = significant.\n")

    for cfg in configs:
        print(f"## {cfg} vs baseline\n")
        print("| dimension | n | mean delta | CI95 | verdict |")
        print("|---|---|---|---|---|")
        for dim in DIMENSIONS + ["weighted_average"]:
            diffs = []
            for r in recs:
                if r["config"] != cfg:
                    continue
                b = base.get((r["topic_id"], r["seed"]))
                if not b:
                    continue
                rv = r["scores"][dim] if dim in r["scores"] else r[dim]
                bv = b["scores"][dim] if dim in b["scores"] else b[dim]
                diffs.append(rv - bv)
            if not diffs:
                continue
            m = sum(diffs) / len(diffs)
            lo, hi = boot_ci(diffs)
            sig = "**significant**" if (lo > 0 or hi < 0) else "n.s."
            print(f"| {dim} | {len(diffs)} | {m:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {sig} |")
        print()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1
         else "benchmarks/results/zhipu_archive/ablation_20260430_062537.json")
