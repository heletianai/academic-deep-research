"""
JudgeAgent（终审）：综合所有辩论轮次三维打分，输出 ACCEPT / REVISE / REJECT。

Stage 2 红蓝对抗终审环。
"""

from __future__ import annotations

import json
from typing import Any, Literal

from openai import OpenAI

from src.llm_utils import chat_with_retry
from src.prompts.judge import JUDGE_SYSTEM_PROMPT, JUDGE_USER_TEMPLATE


Verdict = Literal["ACCEPT", "REVISE", "REJECT"]


class JudgeAgent:
    """终审：三维打分 + 裁决。"""

    def __init__(
        self,
        llm_client: OpenAI,
        model: str = "deepseek/deepseek-v4-flash",
    ) -> None:
        self.llm = llm_client
        self.model = model

    @staticmethod
    def _format_debate_history(history: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for i, h in enumerate(history, 1):
            critique = h.get("critique", {})
            defense = h.get("defense", {})
            lines.append(f"\n--- Round {i} ---")
            lines.append(f"Critic 质疑：")
            for dim in ("factual", "logical", "citation"):
                items = critique.get(dim, [])
                if items:
                    lines.append(f"  {dim}: {json.dumps(items, ensure_ascii=False)}")
            lines.append(f"Defender 回应：")
            for r in defense.get("responses", []):
                stance = r.get("stance", "?")
                content = r.get("content", "")[:200]
                cites = r.get("citations", [])
                lines.append(f"  [{stance}] {content}  refs={cites}")
            conceded = defense.get("conceded_points", [])
            if conceded:
                lines.append(f"  已承认修正点: {conceded}")
        return "\n".join(lines)

    def run(
        self,
        draft_text: str,
        debate_history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        终审。

        Args:
            draft_text: 经过辩论修正的最终草稿（markdown 或 JSON 串）
            debate_history: [{"critique": ..., "defense": ...}, ...] 所有轮次

        Returns:
            {
                "scores": {"factual": float, "logical": float, "citation": float},
                "average": float,
                "verdict": "ACCEPT" | "REVISE" | "REJECT",
                "reasoning": str,
                "required_revisions": [str, ...]
            }
        """
        # 提取所有轮 conceded_points 拍平
        conceded_all: list[str] = []
        for h in debate_history:
            conceded_all.extend(h.get("defense", {}).get("conceded_points", []))

        user = JUDGE_USER_TEMPLATE.format(
            draft_text=draft_text,
            num_rounds=len(debate_history),
            debate_history=self._format_debate_history(debate_history),
            conceded_points=json.dumps(conceded_all, ensure_ascii=False),
        )

        content = chat_with_retry(
            self.llm,
            model=self.model,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1500,
        )
        try:
            verdict = json.loads(content)
        except json.JSONDecodeError:
            return {
                "scores": {"factual": 0.0, "logical": 0.0, "citation": 0.0},
                "average": 0.0,
                "verdict": "REVISE",
                "reasoning": "JSON 解析失败，默认 REVISE",
                "required_revisions": [],
                "_raw": content,
                "_parse_error": True,
            }

        # 字段保护 + average 兜底计算
        scores = verdict.get("scores", {})
        for d in ("factual", "logical", "citation"):
            scores.setdefault(d, 0.0)
        verdict["scores"] = scores
        if "average" not in verdict:
            verdict["average"] = round(
                (scores["factual"] + scores["logical"] + scores["citation"]) / 3, 3
            )
        verdict.setdefault("verdict", "REVISE")
        verdict.setdefault("reasoning", "")
        verdict.setdefault("required_revisions", [])
        return verdict
