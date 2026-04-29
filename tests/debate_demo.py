"""
Demo：用一个示例研究问题跑通完整的红蓝对抗流程。

Stage 2 实现后，此脚本应能端到端运行：
  python -m tests.debate_demo

当前状态：占位，所有 Agent 尚未实现（NotImplementedError）。
"""

from __future__ import annotations


DEMO_QUERY = (
    "What are the key limitations of chain-of-thought prompting in "
    "large language models, and what recent approaches address them?"
)


def run_demo() -> None:
    """
    跑通完整管线的 demo 入口。

    流程：
    1. 初始化 LLM client（DeepSeek）
    2. 初始化 ArXiv MCP tool
    3. 构建 LangGraph graph
    4. 执行查询，打印每阶段输出
    5. 打印最终裁决和终稿
    """
    raise NotImplementedError(
        "Stage 1 + 2 待实现后启用。"
        "预期流程：researcher → critic → defender → judge → final_draft"
    )


if __name__ == "__main__":
    run_demo()
