"""
JudgeAgent：红蓝对抗终审，决定接受 / 推翻 / 要求补充。

Stage 2 辩论终审组件。
评判标准：三维中多数（≥2/3）通过则接受终稿，否则触发重写或补充。
"""

from __future__ import annotations

from typing import Any, Literal


# 终审裁决类型
Verdict = Literal["ACCEPT", "REVISE", "REJECT"]


class JudgeAgent:
    """
    Stage 2 — 终审 Judge Agent。

    职责：
    1. 接收完整辩论记录（初稿 + 所有轮次 Critic/Defender 记录）
    2. 按三维（事实 / 逻辑 / 引用）逐项打分
    3. 输出裁决：ACCEPT（接受）/ REVISE（要求修正）/ REJECT（推翻重写）
    4. ACCEPT 时合并 Defender 已承认的修正点，输出终稿

    输出格式（dict）：
        {
            "verdict": Verdict,
            "scores": {"factual": float, "logical": float, "citation": float},
            "reasoning": str,
            "final_draft": dict  # verdict == ACCEPT 时提供
        }
    """

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def run(
        self,
        draft: dict[str, Any],
        debate_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        终审辩论，输出裁决 + 终稿。

        Args:
            draft: 原始研究草稿
            debate_history: 所有轮次的 [{"critique": ..., "defense": ...}] 记录

        Returns:
            裁决报告 dict，包含 verdict / scores / reasoning / final_draft
        """
        raise NotImplementedError("Stage 2 待实现：JudgeAgent.run()")
