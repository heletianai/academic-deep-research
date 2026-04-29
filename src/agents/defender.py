"""
DefenderAgent：红蓝对抗中的「蓝方」，检索证据回应或主动承认修正。

Stage 2 红蓝对抗组件。
核心原则：先搜再答。搜到证据则回应，搜不到则承认局限并标记修正点。
"""

from __future__ import annotations

from typing import Any


class DefenderAgent:
    """
    Stage 2 — 蓝方 Defender Agent。

    职责：
    1. 接收 CriticAgent 的质疑报告
    2. 针对每条质疑，调用 ArXiv MCP 检索支撑证据
    3. 有证据：构造反驳，附上文献引用
    4. 无证据：承认该维度局限，输出修正建议
    5. 返回结构化回应报告

    输出格式（dict）：
        {
            "responses": list[dict],  # 每条质疑的回应
            "conceded": list[str],    # 主动承认的修正点
            "revised_draft": dict     # 修正后草稿（可选，承认后更新）
        }
    """

    def __init__(self, llm: Any, arxiv_tool: Any) -> None:
        self.llm = llm
        self.arxiv_tool = arxiv_tool

    def run(
        self,
        draft: dict[str, Any],
        critique: dict[str, Any],
    ) -> dict[str, Any]:
        """
        回应 Critic 质疑，先检索后作答。

        Args:
            draft: 当前研究草稿
            critique: CriticAgent 输出的质疑报告

        Returns:
            结构化回应报告 dict
        """
        raise NotImplementedError("Stage 2 待实现：DefenderAgent.run()")
