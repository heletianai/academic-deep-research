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
                              ⭐ 自研创新点
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Agent 编排 | LangGraph 0.2+ |
| LLM | DeepSeek API（cost-effective）|
| 数据源 | ArXiv MCP + Semantic Scholar MCP |
| 评估 | RAGAs + GEval |
| 包管理 | uv + pyproject.toml |
| Python | 3.12+ |

---

## 差异化对比

| 维度 | LangChain open_deep_research | Academic DeepResearch（本项目）|
|------|------------------------------|-------------------------------|
| 领域 | 通用 Web 检索 | 学术专版（ArXiv + Semantic Scholar）|
| 工具协议 | 自定义 Tool | **MCP-First**（标准化工具接口）|
| 质量保障 | 无内建 | **红蓝对抗 Critic-Defender**（自研）|
| 引用处理 | 无 | 引用图谱构建 + 完整性审查 |
| 评估框架 | 无 | RAGAs + GEval 多维打分 |

---

## 快速开始

```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 2. 装依赖（Stage 1 最小集）
pip install openai python-dotenv arxiv

# 3. 配置 API key
cp .env.example .env  # 填入 OPENROUTER_API_KEY

# 4. 跑 Stage 1 demo（约 30-60 秒）
python -m tests.researcher_demo

# 5. 跑 Stage 2 红蓝对抗端到端 demo（约 5-10 分钟）
python -m tests.debate_demo
```

输出落盘到 `outputs/`：
- Stage 1: `stage1_draft_<ts>.md` — 初稿（背景 / 方法 / 发现 + 真实 ArXiv 引用）
- Stage 2: `debate_<ts>.md` — 完整辩论报告（初稿 + 每轮 Critic/Defender + Judge 裁决）

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

### ☐ Stage 3 — 多源 + 评估
- Semantic Scholar MCP 接入（第二数据源）
- 并行多 Researcher Agent
- RAGAs 自动评估（faithfulness / answer_relevancy）
- 引用图谱可视化

---

## 项目状态

| Stage | 状态 |
|-------|------|
| Stage 1：单 Researcher + ArXiv 初稿 | ☑ 已完成 |
| Stage 2：红蓝对抗 Critic-Defender | ☑ 已完成 |
| Stage 3：多源 + RAGAs 评估 | ☐ 待开发 |
