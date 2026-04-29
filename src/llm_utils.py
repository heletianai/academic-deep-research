"""
LLM 调用 helper：带 rate limit 重试的统一 chat completion。

OpenRouter 免费层经常 429，集中处理。
"""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI, RateLimitError, APIError


def chat_with_retry(
    llm: OpenAI,
    *,
    model: str,
    messages: list[dict[str, str]],
    max_retries: int = 4,
    initial_backoff: float = 5.0,
    provider_order: list[str] | None = None,
    **kwargs: Any,
) -> str:
    """
    带指数退避的 chat completion，可强制指定 OpenRouter provider。

    Args:
        provider_order: 优先 provider 列表，例如 ["DeepSeek"] 强制走 DeepSeek 官方
                        而不是 DeepInfra / Together 等免费 reseller。
                        OpenRouter 默认按价格排序路由，但官方 endpoint 通常更稳定。

    Returns:
        message.content (str)
    """
    backoff = initial_backoff
    last_err: Exception | None = None

    # 默认强制走 DeepSeek 官方，避开 DeepInfra 免费层 rate limit
    if provider_order is None:
        provider_order = ["DeepSeek"]

    extra_body = kwargs.pop("extra_body", {}) or {}
    # 不再强制 provider order — model ID 直接选有官方 endpoint 的版本（如 deepseek-v4-flash）

    for attempt in range(1, max_retries + 1):
        try:
            resp = llm.chat.completions.create(
                model=model,
                messages=messages,
                extra_body=extra_body,
                **kwargs,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError as e:
            last_err = e
            print(f"  [LLM] 429 rate limit (attempt {attempt}/{max_retries})，{backoff:.0f}s 后重试 ...")
            time.sleep(backoff)
            backoff *= 2
        except APIError as e:
            status = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
            if status and 500 <= int(status) < 600:
                last_err = e
                print(f"  [LLM] {status} server error (attempt {attempt}/{max_retries})，{backoff:.0f}s 后重试 ...")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

    assert last_err is not None
    raise last_err
