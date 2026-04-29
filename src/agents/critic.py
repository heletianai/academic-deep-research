"""
CriticAgent（红方）：从事实 / 逻辑 / 引用三维质疑研究初稿。

Stage 2 红蓝对抗第一环。无外部工具调用，纯 LLM。
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from src.llm_utils import chat_with_retry
from src.prompts.critic import CRITIC_SYSTEM_PROMPT, CRITIC_USER_TEMPLATE


class CriticAgent:
    """红方：三维质疑（factual / logical / citation）。"""

    def __init__(
        self,
        llm_client: OpenAI,
        model: str = "deepseek/deepseek-v4-flash",
    ) -> None:
        self.llm = llm_client
        self.model = model

    def run(self, draft_text: str, round_num: int = 1) -> dict[str, Any]:
        """
        生成三维 critique。

        Args:
            draft_text: 当前要质疑的草稿（markdown 或 JSON 串）
            round_num: 第几轮辩论（1-based）

        Returns:
            {
                "factual": [str, ...],
                "logical": [str, ...],
                "citation": [str, ...]
            }
        """
        user = CRITIC_USER_TEMPLATE.format(round_num=round_num, draft_text=draft_text)
        content = chat_with_retry(
            self.llm,
            model=self.model,
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=1500,
        )
        try:
            critique = json.loads(content)
        except json.JSONDecodeError:
            return {
                "factual": [],
                "logical": [],
                "citation": [],
                "_raw": content,
                "_parse_error": True,
            }

        for dim in ("factual", "logical", "citation"):
            critique.setdefault(dim, [])
        return critique

    @staticmethod
    def is_empty(critique: dict[str, Any]) -> bool:
        """所有维度都没质疑 → 可提前终止辩论。"""
        return not any(critique.get(d) for d in ("factual", "logical", "citation"))
