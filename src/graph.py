"""
LangGraph 主流程：定义五阶段管线的节点和边。

将 ResearcherAgent / CriticAgent / DefenderAgent / JudgeAgent
组装为 LangGraph StateGraph，控制辩论轮次上限（max_rounds=3）。
"""

from __future__ import annotations

from typing import Any


def build_graph(
    researcher_agent: Any,
    critic_agent: Any,
    defender_agent: Any,
    judge_agent: Any,
    max_rounds: int = 3,
) -> Any:
    """
    构建五阶段 LangGraph StateGraph。

    节点（node）：
        - researcher：Stage 1 初稿生成
        - critic：Stage 2 三维质疑
        - defender：Stage 2 检索回应
        - judge：Stage 2 终审
        - finalize：Stage 5 终稿生成

    条件边（conditional edge）：
        - judge → critic（verdict == REVISE 且 round < max_rounds）
        - judge → finalize（verdict == ACCEPT 或达到轮次上限）

    Args:
        researcher_agent: ResearcherAgent 实例
        critic_agent: CriticAgent 实例
        defender_agent: DefenderAgent 实例
        judge_agent: JudgeAgent 实例
        max_rounds: 最大辩论轮次，默认 3

    Returns:
        编译好的 LangGraph CompiledGraph
    """
    raise NotImplementedError("Stage 1/2 待实现：build_graph()")
