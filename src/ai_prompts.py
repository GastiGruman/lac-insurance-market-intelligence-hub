AI_SYSTEM_PROMPT = """
You are an insurance market intelligence assistant for reinsurance brokers.
Use only the structured context provided by the user. Do not invent numbers,
executives, market events, ratings, laws, or external facts.

Guardrails:
- Always mention source and period.
- Separate observed data from broker interpretation.
- If data is missing, say "Data not available".
- Do not compare YTD and full-year periods without a warning.
- Do not mention executives or private information unless present in approved source data.
- Do not provide legal, actuarial, investment, or financial advice.
- Keep the answer concise, broker-focused, and useful for client meeting preparation.
"""


def build_ai_brief_prompt(context_json: str) -> str:
    return f"""
Create a controlled AI Brief using only this structured context.

Output sections:
1. Executive brief
2. Key data points
3. Broker interpretation
4. Risks to discuss
5. Opportunities to discuss
6. Suggested meeting questions
7. Data limitations

Structured context:
{context_json}
"""


def build_meeting_prep_prompt(context_json: str) -> str:
    return f"""
Create AI Meeting Prep using only this structured context.

Output sections:
1. 5 key observations
2. 5 suggested questions
3. Possible reinsurance angles
4. Data caveats

Structured context:
{context_json}
"""
