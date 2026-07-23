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

---

## 文本层案例（2026-07-23 离线重跑子集，DeepSeek policy + 离线检索源）

> 设定：baseline + debate_2round × 10 topic × 1 seed，检索层用主项目 9,000 篇真实论文池离线注入（`ARXIV_CACHE_ONLY=1`），终稿全文入档。**检索源与 policy 均与原 150 次不同，分数不并入主对照表**；用途=badcase 文本级机制定性。数据：`rerun-0723/ablation_20260722_223532.json`。
> 结果复现第三次确认：10 组配对 9 组掉分、9 组 Judge verdict=REJECT——负结果在（GLM 栈 / DeepSeek 在线栈 / DeepSeek 离线栈）三种设定下方向一致。

### 失败三型（文本级实锤）

**A 型：终稿漂移（revision-notes 冒充终稿）——T09（0.895 → 0.18，Δ−0.715）**

baseline 版是完整综述（五类路由策略、逐条带真实引用）；debate_2round 版的三个章节字段实际内容是：

> background：「补充引用 Hashimoto et al. (2018) 和 Dwork et al. (2012) 关于公平性控制的早期工作。」
> methods：「增加对负载均衡经典方法（如辅助损失函数）的讨论。」
> findings：「（1）明确 NMI 和 ARI 用于聚类评估…（2）补充统计显著性检验结果…」

——这不是综述，是 Critic 的修改意见清单。多轮重写中"对质疑的回应/修改计划"漂移进了草稿字段，最后一轮把 revision-notes 当 final draft 提交，正文实体内容全部丢失（citations 列表仍保留 5 条 → 引用与正文脱钩，Citation Accuracy 崩 0）。T02（Δ−0.285）同型。

**B 型：部分污染 + 占位伪统计——T08（Δ−0.230）**

正文主体保留，但混入元评注语气（「但需进一步通过多次实验和统计检验验证其稳定性」）；findings 中出现「在 XX 任务上平均奖励提升 X%，p<0.05」——**带占位符的编造统计声明**，Faithfulness 直接被判罚。

**C 型：让步缩水**（4 月分数层推断在本批的对应）：Defender 无检索预算（search_per_critique=0），面对质疑只能删减让步，报告变薄。

### 机制定性与工程结论

失败的共同根源：**多轮改写链的出口没有"终稿结构 validator"**——没有任何机制校验"提交物必须是内容型综述而非指令型笔记"，revision-note 可以冒充 final draft 一路通过 Judge（Judge 也是 LLM，对格式漂移不敏感）。

这与姊妹项目 AcademicExtract-R1 的核心设计互为正反例证：那边 schema validator 作为 reward 硬门控（gate）跑在每一步训练里，格式漂移在冒烟期就会被 gate 率曲线抓获；这边的 debate 链恰恰缺同一个部件。修正方向排序：① 终稿出口加结构校验（章节内容型断言 + 指令句式黑名单），② Defender 回应与草稿字段物理分离，③ 给 Defender 真实检索预算——先堵格式洞，再谈信息增量。
