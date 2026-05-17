from __future__ import annotations

import json

from src.ai_utils import AIConfig, call_llm


NEWS_SUMMARY_SYSTEM_PROMPT = """
You summarize source-based insurance news for reinsurance brokers.
Use only the supplied news items. Do not invent facts.
Always cite the item source and date. If dates are missing, say date not available.
Do not provide legal, investment, or financial advice.
Keep the output concise and meeting-prep oriented.
"""


def build_news_summary_prompt(items: list[dict], scope: str) -> str:
    payload = json.dumps(items[:8], ensure_ascii=False, indent=2)
    return f"""
Summarize these news items for this scope: {scope}

Output sections:
1. What happened
2. Why it matters
3. Possible reinsurance relevance
4. Suggested question for client meeting
5. Sources used

News items:
{payload}
"""


def generate_news_ai_summary(config: AIConfig, items: list[dict], scope: str) -> dict:
    if not config.configured:
        return {
            "ok": False,
            "text": "AI features are not configured yet.",
            "error": "missing_configuration",
        }
    if not items:
        return {
            "ok": False,
            "text": "No news items available for AI summary.",
            "error": "no_news_items",
        }
    return call_llm(config, NEWS_SUMMARY_SYSTEM_PROMPT, build_news_summary_prompt(items, scope))
