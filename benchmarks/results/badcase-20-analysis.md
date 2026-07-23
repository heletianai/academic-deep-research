# Badcase 20 分析（分数层，主数据 GLM 150 全量）

> 口径：debate 系配置 vs baseline 的 (topic, seed) 配对，取 weighted 掉分最狠 20 对。
> 文本层素材（final_report 对照）待 ArXiv 解封后由 rerun 子集补充；本分析基于四维分数结构+5 层根因框架。

## 类型分布

- **A 双崩型（忠实度+引用同溃）**：8 条
- **B 引用崩型（改写丢引/伪引）**：7 条
- **C 忠实度崩型（重写引入无支撑 claim）**：5 条

配置分布：{'full': 9, 'debate_2round': 6, 'debate_1round': 5}；领域分布：{'long_context_cross': 4, 'vlm_cross': 4, 'peft_user_familiar': 3, 'rag_user_familiar': 1, 'agent_self_improvement_user_familiar': 2, 'diffusion_cross': 3, 'moe_cross': 2, 'rlhf_cross': 1}

## 20 条明细（按掉分排序）

| # | topic | domain | config | seed | Δweighted | ΔF | ΔC | ΔCA | ΔS | 主崩维度 | 类型 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | T10 | long_context_cross | full | 1 | -0.615 | -0.50 | -0.30 | -1.00 | -0.70 | citation_accuracy | A |
| 2 | T07 | vlm_cross | full | 2 | -0.485 | -0.40 | -0.30 | -1.00 | -0.20 | citation_accuracy | A |
| 3 | T05 | peft_user_familiar | full | 1 | -0.430 | -0.40 | +0.00 | -1.00 | -0.30 | citation_accuracy | A |
| 4 | T10 | long_context_cross | debate_2round | 3 | -0.385 | -0.50 | -0.30 | -0.40 | -0.30 | faithfulness | A |
| 5 | T05 | peft_user_familiar | debate_2round | 3 | -0.370 | -0.40 | +0.00 | -1.00 | +0.00 | citation_accuracy | A |
| 6 | T05 | peft_user_familiar | full | 2 | -0.350 | -0.20 | +0.00 | -1.00 | -0.20 | citation_accuracy | B |
| 7 | T02 | rag_user_familiar | debate_2round | 3 | -0.280 | -0.10 | +0.00 | -1.00 | +0.00 | citation_accuracy | B |
| 8 | T07 | vlm_cross | debate_1round | 3 | -0.270 | -0.50 | +0.00 | +0.00 | -0.60 | structure_coherence | C |
| 9 | T07 | vlm_cross | full | 3 | -0.260 | -0.50 | +0.00 | -0.20 | -0.30 | faithfulness | C |
| 10 | T04 | agent_self_improve | debate_1round | 3 | -0.250 | +0.00 | +0.00 | -1.00 | +0.00 | citation_accuracy | B |
| 11 | T06 | diffusion_cross | debate_1round | 1 | -0.250 | +0.00 | +0.00 | -1.00 | +0.00 | citation_accuracy | B |
| 12 | T06 | diffusion_cross | debate_1round | 3 | -0.250 | +0.00 | +0.00 | -1.00 | +0.00 | citation_accuracy | B |
| 13 | T10 | long_context_cross | debate_2round | 2 | -0.250 | -0.50 | +0.00 | -0.40 | +0.00 | faithfulness | A |
| 14 | T06 | diffusion_cross | full | 1 | -0.250 | -0.50 | +0.00 | -0.40 | +0.00 | faithfulness | A |
| 15 | T10 | long_context_cross | full | 2 | -0.250 | +0.00 | +0.00 | -1.00 | +0.00 | citation_accuracy | B |
| 16 | T09 | moe_cross | full | 3 | -0.242 | -0.40 | +0.00 | -0.25 | -0.30 | faithfulness | C |
| 17 | T08 | rlhf_cross | debate_2round | 3 | -0.240 | -0.30 | +0.00 | -0.60 | +0.00 | citation_accuracy | A |
| 18 | T09 | moe_cross | debate_2round | 2 | -0.240 | -0.40 | +0.00 | +0.00 | -0.60 | structure_coherence | C |
| 19 | T04 | agent_self_improve | full | 2 | -0.240 | -0.10 | +0.00 | -1.00 | +0.20 | citation_accuracy | B |
| 20 | T07 | vlm_cross | debate_1round | 1 | -0.200 | -0.50 | +0.00 | -0.20 | +0.00 | faithfulness | C |

## 结构性发现

- 主崩维度分布：faithfulness 6/20，citation_accuracy 12/20——badcase 的损伤集中在「重写引入无支撑内容」与「改写破坏引用链」，与配对检验的显著负维度完全一致；
- 跨领域 topic 占 14/20（根因 5：跨领域检索基线低，Critic 更易编造质疑→Defender 无检索预算只能重写让步）；
- 2 轮 debate 系配置占 15/20（剂量效应在 badcase 端的体现：多一轮重写多一次损伤机会）。
