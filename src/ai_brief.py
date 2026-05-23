from __future__ import annotations

import json
import re
import unicodedata

import pandas as pd

from src.ai_prompts import AI_SYSTEM_PROMPT, build_ai_brief_prompt, build_meeting_prep_prompt
from src.ai_utils import AIConfig, call_llm
from src.broker_analytics import (
    build_company_brief,
    build_reinsurance_view_context,
    build_reinsurance_wide,
    format_millions,
    format_percentage,
    prepare_premium_claims_summary,
    summarize_reinsurance,
)


def normalize_text(value) -> str:
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.split())


def _records(df: pd.DataFrame, limit: int = 10) -> list[dict]:
    if df is None or df.empty:
        return []
    safe = df.head(limit).copy()
    for col in safe.columns:
        if pd.api.types.is_datetime64_any_dtype(safe[col]):
            safe[col] = safe[col].astype(str)
    return safe.where(pd.notna(safe), None).to_dict(orient="records")


def build_structured_ai_context(
    country: str,
    company: str,
    selected_line: str,
    selected_years: list[int],
    meeting_purpose: str,
    company_df: pd.DataFrame,
    market_df: pd.DataFrame,
    indicadores_df: pd.DataFrame,
    mapped_company: str | None,
    mapped_line: str | None,
    minimum_premium: float,
) -> dict:
    reinsurance_wide = build_reinsurance_wide(
        indicadores_df,
        country,
        company=mapped_company,
        line=mapped_line,
    )
    reinsurance_summary = summarize_reinsurance(reinsurance_wide)
    broker_brief = build_company_brief(
        country=country,
        company=company,
        selected_line=selected_line,
        selected_years=selected_years,
        company_df=company_df,
        market_df=market_df,
        reinsurance_summary=reinsurance_summary,
        minimum_premium=minimum_premium,
    )

    premium_evolution = broker_brief["premium_evolution"].copy()
    if not premium_evolution.empty:
        premium_evolution = premium_evolution.sort_values("year")

    context = {
        "scope": {
            "country": country,
            "company": company,
            "line_of_business": "All lines" if selected_line == "TODOS" else selected_line,
            "years": [int(year) for year in selected_years],
            "meeting_purpose": meeting_purpose,
        },
        "source_and_period": broker_brief.get(
            "source",
            {
                "source": "Data not available",
                "period": "Data not available",
                "records": 0,
            },
        ),
        "observed_data": {
            "premium_evolution": _records(premium_evolution, 20),
            "market_share": _records(broker_brief["market_share"], 20),
            "main_lines": _records(broker_brief["main_lines"], 10),
            "fastest_growing_lines": _records(broker_brief["fastest_growing_lines"], 10),
            "deteriorating_loss_ratio_lines": _records(
                broker_brief["deteriorating_loss_ratio_lines"],
                10,
            ),
            "reinsurance_summary": reinsurance_summary,
            "alerts": broker_brief["alerts"],
            "suggested_questions_from_rules": broker_brief["questions"],
        },
        "methodology": {
            "primary_source": "Fasecolda - Ciudades y Ramos",
            "reinsurance_source": "Fasecolda - Indicadores de Gestion 2025",
            "ratio_rule": "Ratios are recalculated after aggregation and are not summed.",
            "mapping_rule": "Company and line names use formal DuckDB mapping tables where available.",
            "limitations": [
                "Indicadores de Gestion 2025 remains exploratory pending methodology review.",
                "Aggregate lines may duplicate individual lines.",
                "YTD periods should not be compared directly with full-year periods.",
            ],
        },
    }
    return context


def context_to_json(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2, default=str)


def _clean_scalar(value):
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


def _safe_records(df: pd.DataFrame, limit: int = 10) -> list[dict]:
    records = _records(df, limit)
    return [
        {key: _clean_scalar(value) for key, value in record.items()}
        for record in records
    ]


def _latest_record(df: pd.DataFrame) -> dict:
    if df is None or df.empty or "year" not in df.columns:
        return {}
    latest = df.sort_values("year").iloc[-1].to_dict()
    return {key: _clean_scalar(value) for key, value in latest.items()}


def _summarize_market_context(scope_df: pd.DataFrame, selected_years: list[int]) -> dict:
    summary = prepare_premium_claims_summary(scope_df, ["year"])
    latest = _latest_record(summary)
    if summary.empty:
        return {
            "available": False,
            "latest_year": max(selected_years) if selected_years else None,
            "premium": None,
            "claims": None,
            "claims_premiums_ratio": None,
            "records": int(len(scope_df)) if scope_df is not None else 0,
        }
    return {
        "available": True,
        "latest_year": latest.get("year"),
        "premium": latest.get("primas"),
        "claims": latest.get("siniestros"),
        "claims_premiums_ratio": latest.get("siniestralidad"),
        "records": int(len(scope_df)),
        "annual_summary": _safe_records(summary.sort_values("year"), 20),
    }


def _company_ranking(scope_df: pd.DataFrame, latest_year: int | None, minimum_premium: float) -> list[dict]:
    if scope_df is None or scope_df.empty or latest_year is None:
        return []
    latest_scope = scope_df[scope_df["year"] == latest_year].copy()
    summary = prepare_premium_claims_summary(latest_scope, ["company_standard"])
    if summary.empty:
        return []
    total = summary["primas"].sum()
    summary = summary[summary["primas"] >= minimum_premium].copy()
    summary["market_share"] = summary["primas"] / total if total else pd.NA
    summary = summary.sort_values("primas", ascending=False).head(10)
    return _safe_records(summary, 10)


def _line_focus(scope_df: pd.DataFrame, latest_year: int | None, minimum_premium: float) -> list[dict]:
    if scope_df is None or scope_df.empty or latest_year is None:
        return []
    latest_scope = scope_df[scope_df["year"] == latest_year].copy()
    summary = prepare_premium_claims_summary(latest_scope, ["line_of_business_standard"])
    if summary.empty:
        return []
    total = summary["primas"].sum()
    summary = summary[summary["primas"] >= minimum_premium].copy()
    summary["portfolio_share"] = summary["primas"] / total if total else pd.NA
    summary = summary.sort_values("primas", ascending=False).head(10)
    return _safe_records(summary, 10)


def _format_top_line(lines: list[dict]) -> str:
    if not lines:
        return "Data not available"
    top = lines[0]
    return (
        f"{top.get('line_of_business_standard', 'Selected line')} "
        f"({format_percentage(top.get('portfolio_share'))} of premium)"
    )


def _format_top_company(companies: list[dict]) -> str:
    if not companies:
        return "Data not available"
    top = companies[0]
    return (
        f"{top.get('company_standard', 'Selected company')} "
        f"({format_percentage(top.get('market_share'))} market share)"
    )


def build_ai_brief_context(
    market_df: pd.DataFrame,
    selected_country: str,
    selected_company: str,
    selected_lob: str,
    selected_years: list[int],
    meeting_purpose: str,
    brief_type: str,
    indicadores_df: pd.DataFrame | None = None,
    mapped_company: str | None = None,
    mapped_line: str | None = None,
    minimum_premium: float = 0,
    data_status: dict | None = None,
) -> dict:
    years = [int(year) for year in selected_years] if selected_years else []
    scope_df = market_df.copy() if market_df is not None else pd.DataFrame()
    if years and "year" in scope_df.columns:
        scope_df = scope_df[scope_df["year"].isin(years)].copy()
    if selected_lob and selected_lob != "TODOS" and "line_of_business_standard" in scope_df.columns:
        scope_df = scope_df[scope_df["line_of_business_standard"] == selected_lob].copy()

    company_df = scope_df.copy()
    if selected_company and selected_company != "TODAS" and "company_standard" in company_df.columns:
        company_df = company_df[company_df["company_standard"] == selected_company].copy()

    market_context = _summarize_market_context(scope_df, years)
    company_context = _summarize_market_context(company_df, years)
    latest_year = company_context.get("latest_year") or market_context.get("latest_year")
    competitor_context = _company_ranking(scope_df, latest_year, minimum_premium)
    portfolio_context = _line_focus(company_df if selected_company != "TODAS" else scope_df, latest_year, minimum_premium)

    reinsurance_wide = pd.DataFrame()
    market_reinsurance_wide = pd.DataFrame()
    reinsurance_context = {
        "available": False,
        "selected_summary": {},
        "market_benchmark": {},
        "by_line": [],
        "evolution": [],
        "signals": [],
        "broker_questions": [],
    }
    if indicadores_df is not None and not indicadores_df.empty:
        reinsurance_wide = build_reinsurance_wide(
            indicadores_df,
            selected_country,
            company=mapped_company if selected_company != "TODAS" else None,
            line=mapped_line if selected_lob != "TODOS" else None,
        )
        market_reinsurance_wide = build_reinsurance_wide(
            indicadores_df,
            selected_country,
            line=mapped_line if selected_lob != "TODOS" else None,
        )
        re_ctx = build_reinsurance_view_context(
            selected_wide=reinsurance_wide,
            market_wide=market_reinsurance_wide,
            selected_company=selected_company,
            selected_line=selected_lob,
            minimum_premium=minimum_premium,
        )
        reinsurance_context = {
            "available": re_ctx.get("available", False),
            "executive_snapshot": re_ctx.get("executive_snapshot", []),
            "selected_summary": re_ctx.get("selected_summary", {}),
            "market_benchmark": re_ctx.get("market_benchmark", {}),
            "by_line": _safe_records(re_ctx.get("by_line", pd.DataFrame()), 10),
            "evolution": _safe_records(re_ctx.get("evolution", pd.DataFrame()), 10),
            "signals": re_ctx.get("signals", []),
            "broker_questions": re_ctx.get("broker_questions", []),
        }

    company_brief_context = {}
    broker_questions = []
    alerts = []
    if selected_company != "TODAS":
        reinsurance_summary = summarize_reinsurance(reinsurance_wide)
        brief = build_company_brief(
            country=selected_country,
            company=selected_company,
            selected_line=selected_lob,
            selected_years=years,
            company_df=company_df,
            market_df=scope_df,
            reinsurance_summary=reinsurance_summary,
            minimum_premium=minimum_premium,
            reinsurance_wide=reinsurance_wide,
        )
        company_brief_context = {
            "executive_summary": brief.get("executive_summary"),
            "executive_snapshot": brief.get("executive_snapshot", []),
            "market_position": brief.get("market_position", {}),
            "competitors": _safe_records(brief.get("competitors", pd.DataFrame()), 10),
            "portfolio_mix": _safe_records(brief.get("portfolio_mix", pd.DataFrame()), 10),
            "portfolio_interpretation": brief.get("portfolio_interpretation"),
        }
        broker_questions = brief.get("questions", [])
        alerts = brief.get("alerts", [])
    else:
        broker_questions = [
            "Which companies should be prioritized for a deeper treaty conversation?",
            "Which lines show the most material premium and Claims / Premiums movement?",
            "Where should source data be validated before formal external use?",
        ]

    technical_signals = alerts + reinsurance_context.get("signals", [])

    return {
        "selection": {
            "country": selected_country,
            "company": selected_company,
            "line_of_business": "All lines" if selected_lob == "TODOS" else selected_lob,
            "years": years,
            "meeting_purpose": meeting_purpose,
            "brief_type": brief_type,
        },
        "market_context": market_context,
        "company_context": company_context,
        "portfolio_context": {
            "top_lines": portfolio_context,
            "top_line_summary": _format_top_line(portfolio_context),
        },
        "competitor_context": {
            "top_companies": competitor_context,
            "market_leader_summary": _format_top_company(competitor_context),
        },
        "company_brief_context": company_brief_context,
        "technical_signals": technical_signals,
        "reinsurance_context": reinsurance_context,
        "broker_questions": broker_questions,
        "data_status": data_status or {},
        "methodology_notes": [
            "The brief uses internal structured data from the app database and app-calculated summaries.",
            "Primary source: Fasecolda - Ciudades y Ramos.",
            "Claims / Premiums is an analytical claims-to-premium ratio, not necessarily official technical siniestralidad or combined ratio.",
            "Reinsurance indicators use Fasecolda - Indicadores de Gestion 2025 where available and remain exploratory.",
        ],
        "limitations": [
            "No external news, ratings, financial statements, leadership/key people, or live web search are included in this phase.",
            "No external AI API is required for this deterministic brief.",
            "Figures should be validated against source files before formal client or market presentations.",
        ],
    }


def _brief_focus_sentence(brief_type: str) -> str:
    focus = {
        "Pre-meeting company brief": "Focus on company position, competitors, portfolio priorities and meeting questions.",
        "Reinsurance discussion brief": "Focus on cession, retention, ceded premium and treaty discussion angles.",
        "Portfolio review brief": "Focus on line concentration, growth, Claims / Premiums and technical signals.",
        "Market comparison brief": "Focus on market position, company ranking and competitor benchmark.",
        "Internal strategy brief": "Focus on where a treaty broker may add value through analysis, capacity discussion and source validation.",
    }
    return focus.get(brief_type, focus["Pre-meeting company brief"])


def _markdown_signal_list(signals: list[dict], limit: int = 6) -> str:
    if not signals:
        return "- No material structured-data signal was available under the selected filters."
    lines = []
    for signal in signals[:limit]:
        title = signal.get("title") or signal.get("signal_type") or "Signal"
        severity = signal.get("severity", "Signal")
        explanation = signal.get("explanation", "Review with available data.")
        follow_up = signal.get("follow_up", "Validate before formal use.")
        lines.append(f"- **{severity}: {title}.** {explanation} Broker follow-up: {follow_up}")
    return "\n".join(lines)


def generate_ai_brief_from_context(context: dict) -> str:
    selection = context.get("selection", {})
    market = context.get("market_context", {})
    company = context.get("company_context", {})
    competitors = context.get("competitor_context", {})
    portfolio = context.get("portfolio_context", {})
    reinsurance = context.get("reinsurance_context", {})
    brief_type = selection.get("brief_type", "Pre-meeting company brief")
    selected_company = selection.get("company", "TODAS")
    selected_line = selection.get("line_of_business", "All lines")
    latest_year = company.get("latest_year") or market.get("latest_year") or "N/A"

    scope_label = (
        f"{selected_company} / {selected_line}"
        if selected_company != "TODAS"
        else f"Selected market / {selected_line}"
    )
    premium = company.get("premium") if selected_company != "TODAS" else market.get("premium")
    claims_ratio = (
        company.get("claims_premiums_ratio")
        if selected_company != "TODAS"
        else market.get("claims_premiums_ratio")
    )
    re_summary = reinsurance.get("selected_summary", {})
    re_text = (
        f"Ceded premium {format_millions(re_summary.get('reinsurance_ceded_premium'))}, "
        f"cession ratio {format_percentage(re_summary.get('cession_ratio'))}, "
        f"retention ratio {format_percentage(re_summary.get('retention_ratio'))}."
        if reinsurance.get("available")
        else "Reinsurance indicators are not available for this selection."
    )
    questions = context.get("broker_questions", []) + reinsurance.get("broker_questions", [])
    questions = list(dict.fromkeys([q for q in questions if q]))[:8]
    if not questions:
        questions = ["What source data should be validated before the meeting?"]

    lines = [
        f"# Internal Data AI Brief - {scope_label}",
        "",
        f"**Use case:** {brief_type}. {_brief_focus_sentence(brief_type)}",
        f"**Source period:** latest available selected year {latest_year}.",
        "",
        "## 1. Executive Summary",
        f"- Based on available structured data, the selected scope shows premium of {format_millions(premium)} and Claims / Premiums of {format_percentage(claims_ratio)}.",
        f"- Market leader context: {competitors.get('market_leader_summary', 'Data not available')}.",
        f"- Portfolio focus: {portfolio.get('top_line_summary', 'Data not available')}.",
        f"- Reinsurance angle: {re_text}",
        "",
        "## 2. Market Position",
    ]

    company_brief = context.get("company_brief_context", {})
    market_position = company_brief.get("market_position", {}) if isinstance(company_brief, dict) else {}
    if selected_company != "TODAS" and market_position:
        lines.extend(
            [
                f"- Market share: {format_percentage(market_position.get('market_share'))}.",
                f"- Premium rank: {market_position.get('rank', 'N/A')} of {market_position.get('company_count', 'N/A')} companies in the selected market.",
                f"- Company Claims / Premiums: {format_percentage(market_position.get('company_claims_premiums'))}; selected market Claims / Premiums: {format_percentage(market_position.get('market_claims_premiums'))}.",
            ]
        )
    else:
        lines.append("- Company-specific position is not shown because the selected company is TODAS or data is unavailable.")

    lines.extend(
        [
            "",
            "## 3. Portfolio and Line of Business Focus",
        ]
    )
    top_lines = portfolio.get("top_lines", [])
    if top_lines:
        for row in top_lines[:5]:
            lines.append(
                f"- {row.get('line_of_business_standard')}: premium {format_millions(row.get('primas'))}, "
                f"portfolio share {format_percentage(row.get('portfolio_share'))}, Claims / Premiums {format_percentage(row.get('siniestralidad'))}."
            )
    else:
        lines.append("- Line-level portfolio data is not available under the selected filters.")

    lines.extend(
        [
            "",
            "## 4. Performance and Technical Signals",
            _markdown_signal_list(context.get("technical_signals", []), 6),
            "",
            "## 5. Reinsurance Discussion Angles",
        ]
    )
    if reinsurance.get("available"):
        by_line = reinsurance.get("by_line", [])
        lines.append(f"- Selected reinsurance summary: {re_text}")
        if by_line:
            top = by_line[0]
            lines.append(
                f"- Main ceded line: {top.get('line_of_business_standard')} with ceded premium "
                f"{format_millions(top.get('reinsurance_ceded_premium'))} and cession ratio {format_percentage(top.get('cession_ratio'))}."
            )
        for signal in reinsurance.get("signals", [])[:3]:
            lines.append(f"- {signal.get('title', 'Reinsurance signal')}: {signal.get('explanation', '')}")
    else:
        lines.append("- Reinsurance indicators are not available or not mapped for the selected filters.")

    lines.extend(
        [
            "",
            "## 6. Broker Talking Points",
            "- Use observed premium, Claims / Premiums, portfolio concentration and reinsurance behavior as discussion prompts, not final conclusions.",
            "- Prioritize validation of any figure that will be used in a formal client, market, actuarial or financial presentation.",
            "- Separate observed data from interpretation when discussing technical movement.",
            "",
            "## 7. Suggested Meeting Questions",
        ]
    )
    lines.extend([f"- {question}" for question in questions])

    lines.extend(
        [
            "",
            "## 8. Methodology and Data Limitations",
        ]
    )
    lines.extend([f"- {note}" for note in context.get("methodology_notes", [])])
    lines.extend([f"- {limitation}" for limitation in context.get("limitations", [])])
    lines.extend(
        [
            "",
            "## 9. Next Steps for Broker Preparation",
            "- Validate key figures against source files if the output will be used formally.",
            "- Review whether selected line and company mappings match the intended business entity and portfolio.",
            "- Identify which observations require client confirmation versus market-source validation.",
        ]
    )
    return "\n".join(lines)


def answer_ai_brief_question(question: str, context: dict) -> str:
    question_clean = str(question or "").strip()
    if not question_clean:
        return "Enter a focused internal-data question or use the full brief below."

    q_norm = normalize_text(question_clean)
    reinsurance = context.get("reinsurance_context", {})
    competitors = context.get("competitor_context", {})
    portfolio = context.get("portfolio_context", {})
    questions = context.get("broker_questions", []) + reinsurance.get("broker_questions", [])

    if any(token in q_norm for token in ["REINSURANCE", "REASEGURO", "CESSION", "CESION", "RETENTION", "RETENCION", "CEDIDO"]):
        if not reinsurance.get("available"):
            return "Reinsurance indicators are not available for this selection. Review the full Reinsurance View or mapping coverage before the meeting."
        signals = reinsurance.get("signals", [])
        answer = ["### Reinsurance discussion angles"]
        summary = reinsurance.get("selected_summary", {})
        answer.append(
            f"- Ceded premium: {format_millions(summary.get('reinsurance_ceded_premium'))}; "
            f"cession ratio: {format_percentage(summary.get('cession_ratio'))}; "
            f"retention ratio: {format_percentage(summary.get('retention_ratio'))}."
        )
        answer.append(_markdown_signal_list(signals, 4))
        return "\n".join(answer)

    if any(token in q_norm for token in ["COMPETITOR", "COMPETIDOR", "RANK", "POSITION", "POSICION"]):
        top = competitors.get("top_companies", [])
        if not top:
            return "Competitor context is not available under the selected filters."
        lines = ["### Main competitors / market leaders"]
        for row in top[:8]:
            lines.append(
                f"- {row.get('company_standard')}: premium {format_millions(row.get('primas'))}, "
                f"market share {format_percentage(row.get('market_share'))}, Claims / Premiums {format_percentage(row.get('siniestralidad'))}."
            )
        return "\n".join(lines)

    if any(token in q_norm for token in ["SOAT", "LINE", "LOB", "RAMO", "PORTFOLIO", "CARTERA"]):
        top_lines = portfolio.get("top_lines", [])
        if not top_lines:
            return "Line-of-business context is not available under the selected filters."
        lines = ["### Portfolio / line-of-business focus"]
        for row in top_lines[:6]:
            lines.append(
                f"- {row.get('line_of_business_standard')}: premium {format_millions(row.get('primas'))}, "
                f"share {format_percentage(row.get('portfolio_share'))}, Claims / Premiums {format_percentage(row.get('siniestralidad'))}."
            )
        if "SOAT" in q_norm:
            lines.append("- SOAT caution: compare carefully with official technical views because methodology may differ from the app's analytical Claims / Premiums ratio.")
        return "\n".join(lines)

    if any(token in q_norm for token in ["QUESTION", "PREGUNTA", "ASK", "MEETING", "REUNION"]):
        if not questions:
            return "No specific questions were generated for this selection. Validate source coverage and refine filters."
        return "### Suggested meeting questions\n" + "\n".join(f"- {question}" for question in list(dict.fromkeys(questions))[:8])

    if any(token in q_norm for token in ["VALIDATE", "VALIDAR", "LIMITATION", "LIMITACION", "CAVEAT", "CAUTION"]):
        notes = context.get("methodology_notes", []) + context.get("limitations", [])
        return "### Methodology and validation notes\n" + "\n".join(f"- {note}" for note in notes)

    return (
        "This controlled version can answer questions about reinsurance, competitors, portfolio/lines, "
        "meeting questions and validation notes. The full deterministic AI Brief below is generated from internal structured data."
    )


def generate_ai_brief(config: AIConfig, context: dict) -> dict:
    if not config.configured:
        return {
            "ok": False,
            "text": "AI features are not configured yet.",
            "error": "missing_configuration",
        }
    return call_llm(config, AI_SYSTEM_PROMPT, build_ai_brief_prompt(context_to_json(context)))


def generate_ai_meeting_prep(config: AIConfig, context: dict) -> dict:
    if not config.configured:
        return {
            "ok": False,
            "text": "AI features are not configured yet.",
            "error": "missing_configuration",
        }
    return call_llm(config, AI_SYSTEM_PROMPT, build_meeting_prep_prompt(context_to_json(context)))


def _extract_year(question: str, fallback_year: int) -> int:
    match = re.search(r"\b(20\d{2})\b", question)
    return int(match.group(1)) if match else int(fallback_year)


def _find_line(question: str, available_lines: list[str], selected_line: str) -> str | None:
    if selected_line and selected_line != "TODOS":
        return selected_line
    q_norm = normalize_text(question)
    for line in available_lines:
        if normalize_text(line) in q_norm:
            return line
    return None


def _find_company(question: str, available_companies: list[str], selected_company: str) -> str | None:
    if selected_company and selected_company != "TODAS":
        return selected_company
    q_norm = normalize_text(question)
    for company in available_companies:
        if normalize_text(company) in q_norm:
            return company
    return None


def answer_ask_data(
    question: str,
    market_df: pd.DataFrame,
    indicadores_df: pd.DataFrame,
    country: str,
    selected_company: str,
    selected_line: str,
    selected_years: list[int],
    minimum_premium: float,
) -> dict:
    question_clean = str(question or "").strip()
    if not question_clean:
        return {"answered": False, "answer": "Ask a broker-focused question about the available data."}

    q_norm = normalize_text(question_clean)
    latest_year = max(selected_years) if selected_years else int(market_df["year"].max())
    year = _extract_year(question_clean, latest_year)
    available_lines = sorted(market_df["line_of_business_standard"].dropna().astype(str).unique())
    available_companies = sorted(market_df["company_standard"].dropna().astype(str).unique())

    if any(token in q_norm for token in ["GROW", "GREW", "CREC", "MAYOR CRECIMIENTO"]):
        line = _find_line(question_clean, available_lines, selected_line)
        data = market_df.copy()
        if line:
            data = data[data["line_of_business_standard"] == line]
        summary = prepare_premium_claims_summary(data, ["company_standard", "year"])
        if summary.empty:
            return {"answered": True, "answer": "Data not available for that growth question."}
        summary = summary.sort_values(["company_standard", "year"])
        summary["premium_growth"] = summary.groupby("company_standard")["primas"].pct_change()
        result = (
            summary[
                (summary["year"] == year)
                & (summary["primas"] >= minimum_premium)
                & summary["premium_growth"].notna()
            ]
            .sort_values("premium_growth", ascending=False)
            .head(10)
        )
        if result.empty:
            return {"answered": True, "answer": "Data not available for that growth question."}
        lines = [
            f"- {row.company_standard}: {format_percentage(row.premium_growth)} premium growth, "
            f"{format_millions(row.primas)} premiums in {int(row.year)}."
            for row in result.itertuples()
        ]
        line_text = f" in {line}" if line else ""
        return {
            "answered": True,
            "answer": (
                f"Highest premium growth companies{line_text} in {year}.\n"
                f"Source: Fasecolda - Ciudades y Ramos.\n" + "\n".join(lines)
            ),
        }

    if any(token in q_norm for token in ["COMPARE", "COMPARA", "VERSUS", "VS"]):
        company = _find_company(question_clean, available_companies, selected_company)
        if not company:
            return {"answered": True, "answer": "Data not available: select or name a company to compare."}
        company_df = market_df[market_df["company_standard"] == company]
        company_summary = prepare_premium_claims_summary(company_df, ["year"])
        market_summary = prepare_premium_claims_summary(market_df, ["year"])
        latest_company = company_summary[company_summary["year"] == year]
        latest_market = market_summary[market_summary["year"] == year]
        if latest_company.empty or latest_market.empty:
            return {"answered": True, "answer": "Data not available for that company comparison."}
        company_premium = latest_company["primas"].sum()
        market_premium = latest_market["primas"].sum()
        share = company_premium / market_premium if market_premium else pd.NA
        company_lr = latest_company["siniestros"].sum() / company_premium if company_premium else pd.NA
        market_lr = latest_market["siniestros"].sum() / market_premium if market_premium else pd.NA
        return {
            "answered": True,
            "answer": (
                f"{company} compared with the selected market in {year}.\n"
                f"Source: Fasecolda - Ciudades y Ramos.\n"
                f"- Company premiums: {format_millions(company_premium)}.\n"
                f"- Selected market premiums: {format_millions(market_premium)}.\n"
                f"- Market share: {format_percentage(share)}.\n"
                f"- Company Claims / Premiums ratio: {format_percentage(company_lr)}.\n"
                f"- Selected market Claims / Premiums ratio: {format_percentage(market_lr)}.\n"
                "Note: this is an analytical claims-to-premium ratio, not necessarily Fasecolda's official technical loss ratio or combined ratio."
            ),
        }

    if any(token in q_norm for token in ["CESSION", "CESION", "CEDIDO", "REINSURANCE", "REASEGURO"]):
        re_wide = build_reinsurance_wide(indicadores_df, country)
        if re_wide.empty:
            return {"answered": True, "answer": "Data not available: reinsurance table is not loaded."}
        if any(token in q_norm for token in ["COMPAN", "COMPANIA", "COMPAÑIA"]):
            group_col = "company_standard"
            label = "companies"
        else:
            group_col = "line_of_business_standard"
            label = "lines of business"
        summary = (
            re_wide.groupby(["year", group_col], as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
            )
        )
        summary["cession_ratio"] = (
            summary["reinsurance_ceded_premium"] / summary["gross_written_premium"].replace({0: pd.NA})
        )
        result = summary.dropna(subset=["cession_ratio"]).sort_values("cession_ratio", ascending=False).head(10)
        if result.empty:
            return {"answered": True, "answer": "Data not available for cession ratio."}
        lines = [
            f"- {row[group_col]}: {format_percentage(row['cession_ratio'])}, "
            f"ceded premium {format_millions(row['reinsurance_ceded_premium'])}."
            for _, row in result.iterrows()
        ]
        return {
            "answered": True,
            "answer": (
                f"Highest exploratory cession ratio {label}.\n"
                "Source: Fasecolda - Indicadores de Gestion 2025. "
                "Status: exploratory pending methodology review.\n"
                + "\n".join(lines)
            ),
        }

    if any(token in q_norm for token in ["QUESTIONS", "PREGUNTAS", "MEETING", "REUNION"]):
        company = _find_company(question_clean, available_companies, selected_company) or "the selected company"
        return {
            "answered": True,
            "answer": (
                f"Five meeting questions for {company} based on the selected data:\n"
                "- What explains the latest premium movement versus the prior available year?\n"
                "- Which lines are driving claims-to-premium pressure or improvement?\n"
                "- Are growth targets aligned with underwriting discipline and pricing actions?\n"
                "- Where could reinsurance limits, retention, reinstatements, or exclusions be reviewed?\n"
                "- What data should be validated before using this analysis in a client discussion?\n"
                "Source: generated from available structured Fasecolda data and selected filters."
            ),
        }

    return {
        "answered": False,
        "answer": (
            "Data not available for this question in the controlled first version. "
            "Try asking about premium growth, company comparison, cession ratio, or meeting questions."
        ),
    }
