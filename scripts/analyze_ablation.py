"""
项目 2 Ablation 分析脚本：从 ablation_*.json 出 4 张图 + markdown 表 + 简历金句草稿。

跑法：
    # 自动找最新 ablation_*.json
    python -m scripts.analyze_ablation

    # 指定文件
    python -m scripts.analyze_ablation --input benchmarks/results/ablation_20260429_xxx.json

输出：
    benchmarks/figures/dimension_radar.png      4 维雷达图（5 配置对比）
    benchmarks/figures/config_bar.png           每配置加权平均柱状图
    benchmarks/figures/variance_box.png         3 seed 方差箱线图
    benchmarks/figures/elapsed_cost.png         每配置耗时 + 调用成本
    benchmarks/results/ablation_summary.md      markdown 汇总表
    benchmarks/results/headlines.md             3 版简历金句（保守/标准/激进）
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).parent.parent

DIMENSIONS = ["faithfulness", "coverage", "citation_accuracy", "structure_coherence"]
DIM_LABELS = ["Faithfulness", "Coverage", "Citation Acc.", "Structure"]


def latest_ablation_json() -> Path:
    """找 benchmarks/results/ 下最新的 ablation_*.json。"""
    files = sorted((ROOT / "benchmarks" / "results").glob("ablation_*.json"))
    if not files:
        raise FileNotFoundError("No ablation_*.json found in benchmarks/results/")
    return files[-1]


def load_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["records"]


def aggregate_by_config(records: list[dict]) -> dict[str, dict]:
    """按 config 聚合：4 维均值 / 加权平均 / 方差 / 耗时。"""
    by_config: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.get("status") == "ok":
            by_config[r["config"]].append(r)

    summary: dict[str, dict] = {}
    for config, runs in by_config.items():
        dim_means = {
            d: mean([r["scores"][d] for r in runs]) for d in DIMENSIONS
        }
        dim_stds = {
            d: stdev([r["scores"][d] for r in runs]) if len(runs) > 1 else 0.0
            for d in DIMENSIONS
        }
        weighted_avgs = [r["weighted_average"] for r in runs]
        elapsed = [r["elapsed_sec"] for r in runs]
        summary[config] = {
            "n_runs": len(runs),
            "dim_means": dim_means,
            "dim_stds": dim_stds,
            "weighted_mean": mean(weighted_avgs),
            "weighted_std": stdev(weighted_avgs) if len(weighted_avgs) > 1 else 0.0,
            "elapsed_mean": mean(elapsed),
            "elapsed_total": sum(elapsed),
        }
    return summary


def plot_dimension_radar(summary: dict, out_path: Path) -> None:
    """4 维雷达图：5 配置叠加对比。"""
    configs = list(summary.keys())
    angles = np.linspace(0, 2 * np.pi, len(DIMENSIONS), endpoint=False).tolist()
    angles += angles[:1]  # close polygon

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    colors = plt.cm.tab10(np.linspace(0, 1, len(configs)))

    for config, color in zip(configs, colors):
        values = [summary[config]["dim_means"][d] for d in DIMENSIONS]
        values += values[:1]
        ax.plot(angles, values, color=color, linewidth=2, label=config)
        ax.fill(angles, values, color=color, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIM_LABELS, size=11)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(True)
    ax.set_title("Project 2 Ablation: 4-Dim Quality by Config", size=13, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_config_bar(summary: dict, out_path: Path) -> None:
    """每配置加权平均柱状图（含 errorbar）。"""
    configs = list(summary.keys())
    means = [summary[c]["weighted_mean"] for c in configs]
    stds = [summary[c]["weighted_std"] for c in configs]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0.2, 0.8, len(configs)))
    bars = ax.bar(configs, means, yerr=stds, capsize=5, color=colors, edgecolor="black")
    for bar, m in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{m:.3f}",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    ax.set_ylabel("Weighted Average Quality Score", fontsize=12)
    ax.set_xlabel("Ablation Config", fontsize=12)
    ax.set_title("Project 2 Ablation: Weighted Quality by Config", fontsize=13)
    ax.set_ylim(0, max(means) * 1.2)
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_variance_box(records: list[dict], out_path: Path) -> None:
    """3 seed 方差箱线图（每 config × 每 dimension）。"""
    by_config_dim: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("status") == "ok":
            for d in DIMENSIONS:
                by_config_dim[r["config"]][d].append(r["scores"][d])

    configs = sorted(by_config_dim.keys())
    fig, axes = plt.subplots(1, 4, figsize=(16, 5), sharey=True)
    for ax, dim, label in zip(axes, DIMENSIONS, DIM_LABELS):
        data = [by_config_dim[c][dim] for c in configs]
        ax.boxplot(data, labels=configs, showmeans=True)
        ax.set_title(label, fontsize=11)
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    axes[0].set_ylabel("Score")
    fig.suptitle("Project 2: Per-Dimension Variance Across Seeds", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_elapsed_cost(summary: dict, out_path: Path) -> None:
    """每配置平均耗时 + 总调用次数。"""
    configs = list(summary.keys())
    elapsed_mean = [summary[c]["elapsed_mean"] for c in configs]
    n_runs = [summary[c]["n_runs"] for c in configs]

    fig, ax1 = plt.subplots(figsize=(10, 6))
    color1 = "tab:blue"
    bars = ax1.bar(configs, elapsed_mean, color=color1, alpha=0.7, edgecolor="black", label="Avg time/run (s)")
    ax1.set_xlabel("Ablation Config", fontsize=12)
    ax1.set_ylabel("Avg Elapsed (s)", color=color1, fontsize=12)
    ax1.tick_params(axis="y", labelcolor=color1)
    for bar, e in zip(bars, elapsed_mean):
        ax1.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1,
            f"{e:.0f}s",
            ha="center",
            va="bottom",
            fontsize=10,
            color=color1,
        )

    ax2 = ax1.twinx()
    color2 = "tab:red"
    ax2.plot(configs, n_runs, color=color2, marker="o", linewidth=2, label="N successful runs")
    ax2.set_ylabel("# Runs", color=color2, fontsize=12)
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title("Project 2: Cost (Time × Runs) by Config", fontsize=13)
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def write_summary_md(summary: dict, records: list[dict], out_path: Path) -> None:
    """markdown 汇总表 + 关键提升数字。"""
    lines = ["# Project 2 Ablation Summary\n"]
    lines.append(f"- 总记录: {len(records)}（{sum(1 for r in records if r.get('status') == 'ok')} 成功 / {sum(1 for r in records if r.get('status') == 'error')} 失败）")
    lines.append("")

    # 主对比表
    lines.append("## Weighted Quality by Config\n")
    lines.append("| Config | N | Faithfulness | Coverage | Citation Acc. | Structure | Weighted Avg | Avg Time |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c, s in summary.items():
        lines.append(
            f"| {c} | {s['n_runs']} | "
            f"{s['dim_means']['faithfulness']:.3f}±{s['dim_stds']['faithfulness']:.2f} | "
            f"{s['dim_means']['coverage']:.3f}±{s['dim_stds']['coverage']:.2f} | "
            f"{s['dim_means']['citation_accuracy']:.3f}±{s['dim_stds']['citation_accuracy']:.2f} | "
            f"{s['dim_means']['structure_coherence']:.3f}±{s['dim_stds']['structure_coherence']:.2f} | "
            f"**{s['weighted_mean']:.3f}**±{s['weighted_std']:.2f} | "
            f"{s['elapsed_mean']:.1f}s |"
        )
    lines.append("")

    # 关键 delta
    if "baseline" in summary and "full" in summary:
        b = summary["baseline"]["dim_means"]
        f = summary["full"]["dim_means"]
        lines.append("## Key Deltas: full vs baseline\n")
        for d, label in zip(DIMENSIONS, DIM_LABELS):
            delta = f[d] - b[d]
            pct = (delta / b[d] * 100) if b[d] > 0 else 0
            sign = "+" if delta >= 0 else ""
            lines.append(f"- **{label}**: {b[d]:.3f} → {f[d]:.3f} ({sign}{delta:.3f}, {sign}{pct:.1f}%)")
        lines.append("")

    if "baseline" in summary and "debate_2round" in summary:
        b = summary["baseline"]["dim_means"]
        d2 = summary["debate_2round"]["dim_means"]
        lines.append("## Key Deltas: debate_2round vs baseline (debate-only contribution)\n")
        for d, label in zip(DIMENSIONS, DIM_LABELS):
            delta = d2[d] - b[d]
            pct = (delta / b[d] * 100) if b[d] > 0 else 0
            sign = "+" if delta >= 0 else ""
            lines.append(f"- **{label}**: {b[d]:.3f} → {d2[d]:.3f} ({sign}{delta:.3f}, {sign}{pct:.1f}%)")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_headlines(summary: dict, out_path: Path) -> None:
    """3 版简历金句（保守 / 标准 / 激进）。"""
    if "baseline" not in summary or "full" not in summary:
        out_path.write_text("# Headlines\n\nMissing baseline/full configs.\n", encoding="utf-8")
        return

    b = summary["baseline"]
    f = summary["full"]
    db_dim = summary.get("debate_2round", {}).get("dim_means", {})
    b_dim = b["dim_means"]
    f_dim = f["dim_means"]

    faith_delta_pct = ((f_dim["faithfulness"] - b_dim["faithfulness"]) / b_dim["faithfulness"] * 100) if b_dim["faithfulness"] > 0 else 0
    cov_delta_pct = ((f_dim["coverage"] - b_dim["coverage"]) / b_dim["coverage"] * 100) if b_dim["coverage"] > 0 else 0
    weighted_delta_pct = ((f["weighted_mean"] - b["weighted_mean"]) / b["weighted_mean"] * 100) if b["weighted_mean"] > 0 else 0

    debate_only_pct = 0
    if db_dim:
        debate_only_pct = ((db_dim["faithfulness"] - b_dim["faithfulness"]) / b_dim["faithfulness"] * 100) if b_dim["faithfulness"] > 0 else 0

    n_topics = len({r for r in []})  # placeholder, 实际从 records 拿
    n_topics_actual = summary["full"]["n_runs"] // 3 if summary["full"]["n_runs"] >= 3 else summary["full"]["n_runs"]

    lines = ["# 简历金句草稿（3 版本）\n"]

    lines.append("## 保守版（数字对齐 baseline → full 主对比）\n")
    lines.append(
        f"基于 {n_topics_actual} 个学术研究 topic 的 ablation 实验，红蓝对抗 + 多源检索使"
        f"加权综合质量分从 {b['weighted_mean']:.2f} 提升至 {f['weighted_mean']:.2f}（+{weighted_delta_pct:.1f}%）。"
    )
    lines.append("")

    lines.append("## 标准版（拆 Faithfulness 主指标）\n")
    lines.append(
        f"自研 Critic-Defender-Judge 红蓝对抗机制（事实 / 逻辑 / 引用三维质疑），在 {n_topics_actual} 个学术研究 topic 上"
        f" Faithfulness 从 {b_dim['faithfulness']:.2f} 提升至 {f_dim['faithfulness']:.2f}（+{faith_delta_pct:.1f}%），"
        f"Coverage 从 {b_dim['coverage']:.2f} 提升至 {f_dim['coverage']:.2f}（+{cov_delta_pct:.1f}%）。"
    )
    lines.append("")

    lines.append("## 激进版（拆「对抗仅自身贡献」）\n")
    if db_dim:
        lines.append(
            f"5 组 ablation 验证：仅引入红蓝对抗（不加多源）使 Faithfulness 提升 {debate_only_pct:.1f}%；"
            f"叠加多源检索后 full 配置达 Faithfulness {f_dim['faithfulness']:.2f} / Coverage {f_dim['coverage']:.2f} / "
            f"Citation Accuracy {f_dim['citation_accuracy']:.2f} / Structure {f_dim['structure_coherence']:.2f}，"
            f"加权综合 {f['weighted_mean']:.2f} vs baseline {b['weighted_mean']:.2f}。"
        )
    else:
        lines.append("（缺 debate_2round 数据，无法生成激进版）")
    lines.append("")

    lines.append("## 4 维分项对比表\n")
    lines.append("| Dimension | baseline | full | Δ | Δ% |")
    lines.append("|---|---|---|---|---|")
    for d, label in zip(DIMENSIONS, DIM_LABELS):
        bv = b_dim[d]
        fv = f_dim[d]
        delta = fv - bv
        pct = (delta / bv * 100) if bv > 0 else 0
        lines.append(f"| {label} | {bv:.3f} | {fv:.3f} | {delta:+.3f} | {pct:+.1f}% |")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default=None, help="ablation_*.json 路径，默认自动找最新")
    args = parser.parse_args()

    json_path = Path(args.input) if args.input else latest_ablation_json()
    print(f"[analyze] 读取 {json_path}")
    records = load_records(json_path)
    print(f"[analyze] {len(records)} 条记录")

    summary = aggregate_by_config(records)
    print(f"[analyze] {len(summary)} 个 config: {list(summary.keys())}")

    fig_dir = ROOT / "benchmarks" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    print("[analyze] 画 dimension_radar.png ...")
    plot_dimension_radar(summary, fig_dir / "dimension_radar.png")
    print("[analyze] 画 config_bar.png ...")
    plot_config_bar(summary, fig_dir / "config_bar.png")
    print("[analyze] 画 variance_box.png ...")
    plot_variance_box(records, fig_dir / "variance_box.png")
    print("[analyze] 画 elapsed_cost.png ...")
    plot_elapsed_cost(summary, fig_dir / "elapsed_cost.png")

    summary_md = ROOT / "benchmarks" / "results" / "ablation_summary.md"
    write_summary_md(summary, records, summary_md)
    print(f"[analyze] summary md → {summary_md}")

    headlines_md = ROOT / "benchmarks" / "results" / "headlines.md"
    write_headlines(summary, headlines_md)
    print(f"[analyze] headlines md → {headlines_md}")

    print("\n[analyze] 完成")


if __name__ == "__main__":
    main()
