from __future__ import annotations

import json
import re
import unicodedata

import pandas as pd

from src.ai_prompts import AI_SYSTEM_PROMPT, build_ai_brief_prompt, build_meeting_prep_prompt
from src.ai_utils import AIConfig, call_llm
from src.broker_analytics import (
    build_company_brief,
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
                f"- Company loss ratio: {format_percentage(company_lr)}.\n"
                f"- Selected market loss ratio: {format_percentage(market_lr)}."
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
                "- Which lines are driving loss ratio pressure or improvement?\n"
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
