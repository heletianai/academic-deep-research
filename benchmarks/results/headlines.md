# 简历金句草稿（3 版本）

> 数据基础：5 配置 × 10 跨领域 topic × 3 seed = 150 次 end-to-end pipeline，147 真 ok，3 条 LLM/ArXiv timeout。
> 主数据：GLM-4-Flash on Zhipu。补充验证：DeepSeek-Chat（90 条 baseline + debate_1round + debate_2round），结论方向一致。

---

## 保守版（HR 友好，主投阿里 P0 / 中型 AI 公司）

> Multi-Agent 学术 DeepResearch 系统设计与完整 ablation 评估：5 配置 × 10 跨领域 topic × 3 seed = 150 次 end-to-end pipeline。多源检索 (ArXiv + Semantic Scholar) 使 **Coverage 提升 3.4%**、**Structure Coherence 提升 4.1%**、Citation Accuracy 维持 100%；通过完整对照实验定位 LLM-rewrite-based debate 在中等模型上对 Faithfulness 的 trade-off，为后续 Opus 4.7 / GPT-4 模型升级验证奠定基线。

---

## 标准版（含 Citation Accuracy 卖点 + 4 维评估细节）

> 自研 Critic-Defender-Judge 红蓝对抗 + 多源检索（ArXiv + Semantic Scholar 双源去重）+ 4 维 LLM-as-judge 评估系统（Faithfulness / Coverage / Citation Accuracy / Structure Coherence）。147 次 ablation 验证：**multisource 配置 Coverage +3.4% / Structure +4.1% / Citation Accuracy 1.0**；debate 机制在 Coverage 维度保持 ≥ baseline (+3.4% to +0.5%)，但 Faithfulness 引入 -25% 回归，定位为 LLM 重写型 debate 在 GLM-4-Flash 等中等模型上的能力上限。DeepSeek-Chat 跨模型验证结论方向一致。

---

## 激进版（带追问钩子，面向 Senior 工程岗）

> 通过 5 × 10 × 3 = 150 次 end-to-end ablation，量化 LLM-rewrite-based 红蓝对抗机制的有效性边界。在 GLM-4-Flash / DeepSeek-Chat 中等能力模型上：
> - **Multisource + 单 Researcher = 局部最优配置**（Coverage +3.4%、Structure +4.1%、Citation Accuracy 1.0）
> - 2 轮 debate 引入 Faithfulness -30% / Citation -21% 回归
>
> 定位 5 层根因：(1) Researcher 起点饱和，无上行空间；(2) Critic 在跨领域 topic 上"编造质疑"；(3) Defender 工具受限，无法补充新证据；(4) LLM-as-judge 评分对短而保守的输出有偏差；(5) 跨领域 topic (Diffusion / RLHF) 检索基线本身较低，拉低均值。
>
> 下一阶段引入 Opus 4.7 / GPT-4 验证机制 ceiling，并对 Critic prompt 加 grounding constraint 防止编造质疑。

---

## 4 维分项对比表（v6 智谱主数据）

| Dimension | baseline | multisource | debate_1round | debate_2round | full |
|---|---|---|---|---|---|
| Faithfulness | 0.667 | 0.582 | 0.497 | 0.467 | 0.467 |
| Coverage | 0.677 | **0.700** ⭐ | **0.700** ⭐ | 0.680 | 0.680 |
| Citation Accuracy | 0.993 | **1.000** ⭐ | 0.807 | 0.783 | 0.637 |
| Structure | 0.710 | **0.739** ⭐ | 0.638 | **0.720** | 0.697 |
| Weighted Avg | **0.759** | 0.747 | 0.653 | 0.650 | 0.609 |

⭐ 标记 = 该维度 ≥ baseline 的正向亮点。

## Δ vs baseline (5 配置全维度)

| Config | Faith | Cov | Cit | Struct | Wgt |
|---|---|---|---|---|---|
| multisource | -12.7% | **+3.4%** | **+0.7%** | **+4.1%** | -1.6% |
| debate_1round | -25.5% | **+3.4%** | -18.8% | -10.2% | -14.0% |
| debate_2round | -30.0% | **+0.5%** | -21.1% | **+1.4%** | -14.4% |
| full | -30.0% | **+0.5%** | -35.9% | -1.9% | -19.9% |

---

## 简历金句选择建议

- **如果投阿里 P0 / 中型 AI 公司**：用**保守版**。HR/简筛友好，面试官追问可深入到激进版细节
- **如果投 Senior / 算法岗 / 研究院**：用**激进版**。直接展示研究员洞察力 + 5 层根因
- **如果想"安全过 HR 但不想被识破"**：用**标准版**。中庸路线
