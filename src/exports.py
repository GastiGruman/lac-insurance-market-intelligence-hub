from __future__ import annotations

from datetime import datetime
from io import BytesIO
import re

import pandas as pd

from src.broker_analytics import (
    format_millions,
    format_percentage,
    prepare_premium_claims_summary,
)


METHODOLOGY_NOTE = (
    "Incurred Claims / Written Premium is an analytical incurred-claims-to-written-premium ratio and is not necessarily "
    "Fasecolda's official technical siniestralidad or combined ratio. Reinsurance indicators "
    "are exploratory where source limitations apply. External news is curated/manual and may "
    "be empty. Validate outputs before formal client or market presentations."
)


def sanitize_export_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip().lower())
    return safe.strip("_") or "export"


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    if df is None:
        df = pd.DataFrame()
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "data") -> bytes | None:
    if df is None:
        df = pd.DataFrame()
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "data")
        return output.getvalue()
    except Exception:
        return None


def build_export_metadata(
    country: str,
    company: str,
    line_of_business: str,
    years: list[int],
    generated_at: datetime | None = None,
) -> dict:
    generated_at = generated_at or datetime.now()
    return {
        "generated_from": "LAC Insurance Market Intelligence Hub",
        "country": country,
        "company": company,
        "line_of_business": "All lines" if line_of_business == "TODOS" else line_of_business,
        "years": ", ".join(str(int(year)) for year in years) if years else "N/A",
        "data_source": "Fasecolda public data / app-normalized DuckDB database",
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M"),
    }


def _metadata_footer(metadata: dict) -> str:
    return f"""

---

**Export metadata**

- Generated from: {metadata.get("generated_from", "LAC Insurance Market Intelligence Hub")}
- Country: {metadata.get("country", "N/A")}
- Company: {metadata.get("company", "N/A")}
- Line of business: {metadata.get("line_of_business", "N/A")}
- Years: {metadata.get("years", "N/A")}
- Data source: {metadata.get("data_source", "Fasecolda / app-normalized database")}
- Generated at: {metadata.get("generated_at", "N/A")}

**Methodology note:** {METHODOLOGY_NOTE}
"""


def _bullet_list(items: list[str], fallback: str = "Data not available.") -> str:
    clean = [str(item).strip() for item in items if str(item or "").strip()]
    if not clean:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in clean)


def build_company_brief_markdown(brief: dict | None, metadata: dict) -> str:
    if not brief:
        return "# Company Brief\n\nData not available." + _metadata_footer(metadata)
    snapshot = brief.get("executive_snapshot", []) or []
    snapshot_lines = [
        f"{card.get('label')}: {card.get('value')} ({card.get('detail', '')})"
        for card in snapshot
    ]
    competitors = brief.get("competitors")
    competitor_lines = []
    if isinstance(competitors, pd.DataFrame) and not competitors.empty:
        for _, row in competitors.head(5).iterrows():
            competitor_lines.append(
                f"{row.get('company_standard')}: {format_millions(row.get('primas'))}, "
                f"share {format_percentage(row.get('market_share'))}"
            )
    portfolio = brief.get("portfolio_mix")
    portfolio_lines = []
    if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
        for _, row in portfolio.head(5).iterrows():
            portfolio_lines.append(
                f"{row.get('line_of_business_standard')}: {format_millions(row.get('primas'))}, "
                f"portfolio share {format_percentage(row.get('portfolio_share'))}"
            )
    alerts = brief.get("alerts", []) or []
    alert_lines = [
        f"{alert.get('severity', 'Signal')}: {alert.get('title', 'Alert')} - {alert.get('explanation', '')}"
        for alert in alerts[:6]
    ]
    questions = brief.get("questions", []) or []
    return f"""# Company Brief Export - {metadata.get("company", "Selected company")}

## Executive Summary
{brief.get("executive_summary", "Data not available.")}

## Executive Snapshot
{_bullet_list(snapshot_lines)}

## Market Position
- Market share: {format_percentage((brief.get("market_position") or {}).get("market_share"))}
- Premium rank: {(brief.get("market_position") or {}).get("rank", "N/A")} of {(brief.get("market_position") or {}).get("company_count", "N/A")}

## Main Competitors
{_bullet_list(competitor_lines)}

## Portfolio Mix
{_bullet_list(portfolio_lines)}

## Key Technical Signals
{_bullet_list(alert_lines)}

## Reinsurance Preview
{brief.get("reinsurance_text", "Reinsurance indicators are not available for this selection.")}

## Suggested Broker Questions
{_bullet_list(questions)}
""" + _metadata_footer(metadata)


def build_ai_brief_markdown(ai_brief_text: str, metadata: dict) -> str:
    return str(ai_brief_text or "# AI Brief\n\nData not available.") + _metadata_footer(metadata)


def build_reinsurance_summary_markdown(reinsurance_context: dict | None, metadata: dict) -> str:
    context = reinsurance_context or {}
    summary = context.get("selected_summary", {})
    benchmark = context.get("market_benchmark", {})
    by_line = context.get("by_line")
    signals = context.get("signals", []) or []
    questions = context.get("broker_questions", []) or []

    line_rows = []
    if isinstance(by_line, pd.DataFrame) and not by_line.empty:
        for _, row in by_line.head(6).iterrows():
            line_rows.append(
                f"{row.get('line_of_business_standard')}: ceded {format_millions(row.get('reinsurance_ceded_premium'))}, "
                f"cession {format_percentage(row.get('cession_ratio'))}, retention {format_percentage(row.get('retention_ratio'))}"
            )

    signal_lines = [
        f"{signal.get('severity', 'Signal')}: {signal.get('title', 'Signal')} - {signal.get('explanation', '')}"
        for signal in signals[:6]
    ]

    return f"""# Reinsurance Summary Export - {metadata.get("company", "Selected company")}

## Selected Context
- Company: {metadata.get("company", "N/A")}
- Line of business: {metadata.get("line_of_business", "N/A")}
- Years: {metadata.get("years", "N/A")}

## Treaty Metrics
- Emitted premium: {format_millions(summary.get("gross_written_premium"))}
- Retained premium: {format_millions(summary.get("retained_premium"))}
- Ceded premium: {format_millions(summary.get("reinsurance_ceded_premium"))}
- Cession ratio: {format_percentage(summary.get("cession_ratio"))}
- Retention ratio: {format_percentage(summary.get("retention_ratio"))}
- Paid claims / premium: {format_percentage(summary.get("paid_claims_ratio"))}

## Company vs Market
- Cession difference vs market: {format_percentage(benchmark.get("cession_ratio_difference"))}
- Retention difference vs market: {format_percentage(benchmark.get("retention_ratio_difference"))}

## Key Lines by Ceded Premium
{_bullet_list(line_rows)}

## Reinsurance Signals
{_bullet_list(signal_lines)}

## Suggested Treaty Discussion Questions
{_bullet_list(questions)}
""" + _metadata_footer(metadata)


def build_market_summary_markdown(filtered_df: pd.DataFrame, metadata: dict, minimum_premium: float = 0) -> str:
    if filtered_df is None or filtered_df.empty:
        return "# Market Summary\n\nData not available." + _metadata_footer(metadata)
    market_summary = prepare_premium_claims_summary(filtered_df, ["year"])
    latest = market_summary.sort_values("year").iloc[-1] if not market_summary.empty else {}
    company_summary = prepare_premium_claims_summary(filtered_df, ["company_standard"])
    if not company_summary.empty:
        total = company_summary["primas"].sum()
        company_summary = company_summary[company_summary["primas"] >= minimum_premium].copy()
        company_summary["market_share"] = company_summary["primas"] / total if total else pd.NA
        company_summary = company_summary.sort_values("primas", ascending=False).head(8)
    line_summary = prepare_premium_claims_summary(filtered_df, ["line_of_business_standard"])
    if not line_summary.empty:
        total_line = line_summary["primas"].sum()
        line_summary["share"] = line_summary["primas"] / total_line if total_line else pd.NA
        line_summary = line_summary.sort_values("primas", ascending=False).head(8)
    top_companies = [
        f"{row.get('company_standard')}: {format_millions(row.get('primas'))}, share {format_percentage(row.get('market_share'))}"
        for _, row in company_summary.iterrows()
    ] if not company_summary.empty else []
    top_lines = [
        f"{row.get('line_of_business_standard')}: {format_millions(row.get('primas'))}, share {format_percentage(row.get('share'))}"
        for _, row in line_summary.iterrows()
    ] if not line_summary.empty else []
    return f"""# Market Summary Export

## Selected Context
- Country: {metadata.get("country", "N/A")}
- Company filter: {metadata.get("company", "N/A")}
- Line of business: {metadata.get("line_of_business", "N/A")}
- Years: {metadata.get("years", "N/A")}

## Market Metrics
- Latest selected year: {latest.get("year", "N/A") if isinstance(latest, pd.Series) else "N/A"}
- Total premiums: {format_millions(latest.get("primas") if isinstance(latest, pd.Series) else pd.NA)}
- Incurred Claims / Written Premium: {format_percentage(latest.get("siniestralidad") if isinstance(latest, pd.Series) else pd.NA)}

## Top Companies
{_bullet_list(top_companies)}

## Top Lines of Business
{_bullet_list(top_lines)}
""" + _metadata_footer(metadata)


def build_broker_one_pager_markdown(
    company_brief: dict | None,
    ai_brief_text: str,
    reinsurance_context: dict | None,
    metadata: dict,
) -> str:
    brief = company_brief or {}
    questions = brief.get("questions", []) if brief else []
    re_signals = (reinsurance_context or {}).get("signals", []) or []
    re_lines = [
        f"{signal.get('title', 'Reinsurance signal')}: {signal.get('explanation', '')}"
        for signal in re_signals[:3]
    ]
    snapshot = brief.get("executive_snapshot", []) if brief else []
    snapshot_lines = [
        f"{card.get('label')}: {card.get('value')}"
        for card in snapshot[:5]
    ]
    return f"""# Broker One-Pager - {metadata.get("company", "Selected scope")}

## Executive Snapshot
{_bullet_list(snapshot_lines, "Use the AI Brief and Market Summary for this selected scope.")}

## What Changed?
- Review premium movement, Incurred Claims / Written Premium and portfolio mix under the selected filters.
- Use the full AI Brief for a broader internal-data interpretation.

## What Matters For A Broker?
- Focus on market position, portfolio concentration, Incurred Claims / Written Premium movement and reinsurance discussion angles.
- Validate source figures before using them formally.

## Reinsurance Discussion Angles
{_bullet_list(re_lines, "Reinsurance indicators are not available for this selection.")}

## Suggested Questions
{_bullet_list(questions[:6])}
""" + _metadata_footer(metadata)


def build_ppt_ready_bullets(
    company_brief: dict | None,
    reinsurance_context: dict | None,
    metadata: dict,
) -> str:
    bullets = []
    brief = company_brief or {}
    market_position = brief.get("market_position", {}) if brief else {}
    if market_position:
        bullets.append(
            f"Market position: {metadata.get('company')} ranks {market_position.get('rank', 'N/A')} by premium "
            f"with {format_percentage(market_position.get('market_share'))} market share."
        )
    portfolio = brief.get("portfolio_mix") if brief else None
    if isinstance(portfolio, pd.DataFrame) and not portfolio.empty:
        top = portfolio.iloc[0]
        bullets.append(
            f"Portfolio focus: {top.get('line_of_business_standard')} represents "
            f"{format_percentage(top.get('portfolio_share'))} of selected premium."
        )
    re_summary = (reinsurance_context or {}).get("selected_summary", {})
    if re_summary:
        bullets.append(
            f"Reinsurance angle: cession ratio {format_percentage(re_summary.get('cession_ratio'))}, "
            f"retention ratio {format_percentage(re_summary.get('retention_ratio'))}."
        )
    for signal in (reinsurance_context or {}).get("signals", [])[:2]:
        bullets.append(f"Treaty signal: {signal.get('title', 'Signal')} - {signal.get('explanation', '')}")
    for question in brief.get("questions", [])[:3] if brief else []:
        bullets.append(f"Broker question: {question}")
    if not bullets:
        bullets.append("Selected scope: use market summary and filtered data exports for meeting preparation.")
    bullets.append("Methodology: validate figures before formal use; Incurred Claims / Written Premium is analytical.")
    return "\n".join(f"- {bullet}" for bullet in bullets[:10])

