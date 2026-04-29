"""
CriticAgent：红蓝对抗中的「红方」，从三维发起质疑。

Stage 2 红蓝对抗组件。
三维质疑维度：
  - 事实准确性（Factual）：数据 / 数字 / 声明是否可验证？
  - 逻辑一致性（Logical）：结论能从前提严格推出吗？
  - 引用完整性（Citation）：是否遗漏关键相关文献？
"""

from __future__ import annotations

from typing import Any


class CriticAgent:
    """
    Stage 2 — 红方 Critic Agent。

    职责：
    1. 接收研究初稿（draft: dict）
    2. 逐维度生成质疑列表（每维度 1-3 条）
    3. 输出结构化批评报告供 DefenderAgent 回应

    输出格式（dict）：
        {
            "factual": list[str],   # 事实质疑列表
            "logical": list[str],   # 逻辑质疑列表
            "citation": list[str],  # 引用质疑列表
            "round": int            # 当前辩论轮次（1-3）
        }
    """

    def __init__(self, llm: Any) -> None:
        self.llm = llm

    def run(self, draft: dict[str, Any], round_num: int = 1) -> dict[str, Any]:
        """
        生成三维质疑报告。

        Args:
            draft: ResearcherAgent 或上轮修正后的研究初稿
            round_num: 当前辩论轮次，1-indexed，最大 3

        Returns:
            结构化批评报告 dict
        """
        raise NotImplementedError("Stage 2 待实现：CriticAgent.run()")
