# Academic DeepResearch — Multi-Agent 学术深度研究系统

基于红蓝对抗 Critic-Defender 机制的多 Agent 学术研究助手，专为 ArXiv + Semantic Scholar 双源检索与引用质量自动审查设计。

---

## 核心创新：红蓝对抗 Critic-Defender 机制

传统 RAG 生成的研究报告缺乏自我质疑能力。本系统引入**三角色辩论机制**：

```
Researcher → 初稿
    ↓
Critic Agent    ← 从「事实 / 逻辑 / 引用」三维发起质疑
    ↓
Defender Agent  ← 检索新证据回应，或主动承认修正
    ↓
（最多 3 轮辩论）
    ↓
Judge Agent     ← 终审：接受 / 推翻 / 要求补充
    ↓
终稿
```

- **Critic 三维质疑**：事实准确性（数据来源可验证？）、逻辑一致性（结论能从前提推出？）、引用完整性（是否遗漏重要相关文献？）
- **Defender 检索循环**：先搜再答，不空谈；搜不到直接承认局限
- **Judge 终审标准**：多数维度通过则接受，否则触发重写

---

## 五阶段架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Academic DeepResearch Pipeline               │
├──────────┬──────────┬──────────────┬──────────────┬────────────┤
│ Stage 1  │ Stage 2  │   Stage 3    │   Stage 4    │  Stage 5   │
│ 初稿生成  │ 并行调研  │  红蓝对抗    │  多维评估    │  终稿生成  │
│          │          │  Critic ↔    │  RAGAs       │            │
│Researcher│Multi-    │  Defender    │  + GEval     │  Final     │
│  Agent   │Researcher│  Judge       │              │  Report    │
│  + ArXiv │ +Semantic│  (≤3 轮)     │              │            │
└──────────┴──────────┴──────────────┴──────────────┴────────────┘
                          (核心创新)
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 编排 | 自研 graph-based pipeline (LangGraph-style state passing) |
| LLM | Zhipu GLM-4-Flash (默认免费) / DeepSeek-V4 (OpenRouter) 双 provider 切换 |
| 数据源 | ArXiv 直接调用 + Semantic Scholar HTTP API（双源并行 + 去重）|
| 评估 | 4 维 Quality Evaluator（Faithfulness / Coverage / Citation Accuracy / Structure Coherence）+ 自研 RAGAs-lite 三指标 |
| 容器化 | Docker + docker-compose（一键启动）|
| 包管理 | pip + pyproject.toml |
| Python | 3.12+ |

---

## 差异化对比

| 维度 | LangChain open_deep_research | Academic DeepResearch（本项目）|
|------|------------------------------|-------------------------------|
| 领域 | 通用 Web 检索 | 学术专版（ArXiv + Semantic Scholar）|
| 工具协议 | 自定义 Tool | **MCP-First**（标准化工具接口）|
| 质量保障 | 无内建 | **红蓝对抗 Critic-Defender**（自研）|
| 引用处理 | 无 | 引用图谱构建 + 完整性审查 |
| 评估框架 | 无 | 自研 RAGAs-lite 三指标（Faithfulness/Relevance/Precision） |

---

## 快速开始

### Option A: Docker（推荐，一键启动）

```bash
# 1. 配置 API key
cp .env.example .env
# 编辑 .env 填 ZHIPU_API_KEY=xxxx (智谱 GLM-4-Flash 完全免费)
# 或 OPENROUTER_API_KEY=xxxx (DeepSeek paid)

# 2. 一键启动
docker compose up

# 3. 跑 ablation 实验（5 配置 × 10 topic × 3 seed = 150 次）
docker compose --profile ablation up
```

### Option B: 本地 venv

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 装依赖
pip install openai python-dotenv arxiv requests pyyaml matplotlib

# 3. 配置 API key（同上）
cp .env.example .env

# 4. 跑 demo（任选）
python -m tests.researcher_demo         # Stage 1: ~30-60s
python -m tests.debate_demo             # Stage 1+2: ~5-10min
python -m tests.full_pipeline_demo      # Stage 1+2+3: ~12-18min
python -m scripts.run_ablation          # 完整 ablation 5×10×3
python -m scripts.analyze_ablation      # 出 4 张图 + summary
```

### LLM Provider 切换

`.env` 设 `LLM_PROVIDER=zhipu`（默认免费）或 `openrouter`：

| Provider | Model | 价格 | 注册 |
|---|---|---|---|
| Zhipu | `glm-4-flash` | **完全免费** | https://open.bigmodel.cn |
| OpenRouter | `deepseek/deepseek-v4-flash` | ~$0.10/M token | https://openrouter.ai |
| DeepSeek 官方 | `deepseek-chat` | 低价、cache 友好 | https://platform.deepseek.com （`LLM_PROVIDER=deepseek`）|

输出落盘到 `outputs/`：
- Stage 1: `stage1_draft_<ts>.md` — 初稿（背景 / 方法 / 发现 + 真实 ArXiv 引用）
- Stage 2: `debate_<ts>.md` — 完整辩论报告（初稿 + 每轮 Critic/Defender + Judge 裁决）
- Stage 3: `full_pipeline_<ts>.md` — 多源 + 完整辩论 + RAGAs-lite 三指标报告

Demo 输出真实样本：[outputs/](outputs/) （已加入 .gitignore，本地查看）

---

## 路线图

### ☑ Stage 1 — 单 Researcher + ArXiv 初稿
- ✅ 单 Researcher Agent 接收研究问题
- ✅ ArXiv 检索（直接调 arxiv.org/api，Stage 2 升级到 MCP）
- ✅ 结构化初稿输出（背景 / 方法 / 发现 / 引用）
- ✅ 强制 arxiv_id 引用 + 防伪造 prompt
- ✅ Demo 跑通：5 篇真实引用，三段输出

### ☑ Stage 2 — 红蓝对抗（核心创新）
- ✅ Critic Agent：事实 / 逻辑 / 引用三维质疑（默认每维度 1-3 条）
- ✅ Defender Agent：先搜再答 — 有证据 REBUT，无证据 CONCEDE
- ✅ Judge Agent：三维 0.0-1.0 打分 + ACCEPT/REVISE/REJECT 裁决
- ✅ 辩论循环（默认 2 轮，可配置）+ 提前终止（Critic 无质疑时）
- ✅ 端到端 demo 跑通：6 条质疑 → 6 个 CONCEDE → REJECT verdict
- ✅ 带 OpenRouter rate limit 重试 helper（指数退避 4 次）
- 默认模型：DeepSeek V4 Flash（`deepseek/deepseek-v4-flash`）

### ☑ Stage 3 — 多源 + RAGAs-lite 评估
- ✅ Semantic Scholar 直调 API（HTTP，无 MCP 依赖）
- ✅ MultiSourceSearch：ArXiv + Semantic Scholar 并行 + 去重 + 失败 fallback
- ✅ RAGAs-lite 三指标（自研轻量版，LLM judge）：
  - Faithfulness（终稿 claim 是否被 papers 支持）
  - Answer Relevance（终稿是否回答 query）
  - Context Precision（retrieved papers 排序质量）
- ✅ 端到端 demo：Stage 1 → 2 → 3 一次跑通，Judge + RAGAs-lite 双独立打分一致性验证

### ☑ Stage 4 — 4 维 Quality Evaluator + Ablation 实验

升级 RAGAs-lite 三指标 → 4 维 Quality Evaluator，增加引用真实性 + 结构连贯性两个学术综述特有维度。

**4 维评分**（每维 0.0-1.0，加权综合）：

| 维度 | 权重 | 检验 |
|---|---|---|
| **Faithfulness** | 0.30 | 每条 claim 能否被 retrieved papers 支持 |
| **Coverage** | 0.25 | 是否覆盖研究问题的关键子方向（≥4 sub-aspect 满分）|
| **Citation Accuracy** | 0.25 | arxiv_id 真实性（在 papers 列表里）+ 引用 vs claim 匹配度 |
| **Structure Coherence** | 0.20 | Background→Methods→Findings 章节衔接 + 内部一致性 |

**Ablation 实验**：5 配置 × 10 topic × 3 seed = 150 次 pipeline，验证「红蓝对抗 + 多源检索」对各维度的独立贡献。

| Config | 描述 |
|---|---|
| baseline | Researcher only, ArXiv only, 无 debate |
| multisource | + Semantic Scholar，无 debate |
| debate_1round | ArXiv + 1 轮辩论 |
| debate_2round | ArXiv + 2 轮辩论 |
| full | Multisource + 2 轮辩论 |

**测试 topic**（5 用户熟悉领域 + 5 跨领域）：Multi-agent debate / RAG / vLLM / Reflexion / LoRA / Diffusion / VLM / RLHF / MoE / Long-context

跑法：
```bash
python -m scripts.run_ablation        # 跑全量 5×10×3
python -m scripts.analyze_ablation    # 出 4 张图 + summary.md + 简历金句草稿
```

输出：
- `benchmarks/results/ablation_<ts>.json` — 完整 150 条 records
- `benchmarks/results/ablation_summary.md` — 对比表 + 关键 delta
- `benchmarks/results/headlines.md` — 简历金句 3 版（保守 / 标准 / 激进）
- `benchmarks/figures/` — radar / bar / box / cost 4 张图

---

## Ablation 结果与结论（负结果研究）

**主发现：在中等能力模型上，LLM 重写型红蓝对抗不产生质量增益，且显著损伤忠实度与引用准确率。** 这是一个被完整对照实验与跨家族独立复现支撑的负结果。

### 主数据（GLM-4-Flash 全栈，150 次，149 有效）

| Config | Faithfulness | Coverage | Citation Acc. | Structure | Weighted |
|---|---|---|---|---|---|
| baseline | **0.667** | 0.677 | **0.993** | 0.710 | **0.759** |
| multisource | 0.543 | 0.653 | 0.933 | 0.690 | 0.698 |
| debate_1round | 0.497 | 0.700 | 0.807 | 0.638 | 0.653 |
| debate_2round | 0.467 | 0.680 | 0.783 | 0.720 | 0.650 |
| full | 0.467 | 0.680 | 0.637 | 0.697 | 0.609 |

### 配对显著性检验（per topic+seed 配对，bootstrap 95% CI）

- **debate 配置 vs baseline**：Faithfulness −0.18~−0.20、Citation Accuracy −0.19~−0.36，**CI 全部显著**，且 2 轮比 1 轮更差（剂量效应）→ [paired_significance.md](benchmarks/results/paired_significance.md)
- **multisource vs baseline**：四维无一显著增益（Coverage −0.023 n.s.）
- **跨家族独立复现**：DeepSeek 全栈（policy+judge 整栈换家族）90 次同协议实验，debate 回归的方向、显著性、剂量效应全部一致（2 轮：Faithfulness −0.303、Citation −0.303，CI 显著）→ [paired_significance_deepseek.md](benchmarks/results/paired_significance_deepseek.md)——排除"单一 judge 家族偏好短保守输出"的替代解释

### 负结果的 5 层根因

1. Researcher 起点已近饱和，重写无上行空间；2. Critic 在跨领域 topic 上产生"编造质疑"；3. Defender 检索预算受限（`search_per_critique=0`），无法引入新证据、只能重写；4. LLM-as-judge 对短而保守的输出存在评分偏好；5. 跨领域 topic 检索基线低，拉低均值。

**工程结论**：重写型 debate 的失败模式是"无新信息的重写"——修正方向不是加轮数，而是给 Defender 真实检索预算（信息增量）或换更强基座（能力增量）。

> 诚实修正注记（2026-07-23 复审）：早期 headline 草稿中 "multisource Coverage +3.4% / Structure +4.1%" 与主数据矛盾（multisource 实测四维均低于 baseline），已废弃。本节所有数字可由 `scripts/paired_test.py` 对入库原始 JSON 一键复现。

---

## 项目状态

| Stage | 状态 |
|-------|------|
| Stage 1：单 Researcher + ArXiv 初稿 | ☑ 已完成 |
| Stage 2：红蓝对抗 Critic-Defender | ☑ 已完成 |
| Stage 3：多源 + RAGAs-lite 评估 | ☑ 已完成 |
| Stage 4：4 维 Quality Evaluator + Ablation | ☑ 已完成 |
