from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd


DISPLAY_COLUMN_NAMES = {
    "siniestralidad": "Claims / Premiums",
    "loss_ratio_change": "Change in Claims / Premiums",
}


def format_millions(value):
    if pd.isna(value):
        return "N/A"
    return f"COP {value / 1_000_000:,.0f} MM"


def format_percentage(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def safe_divide(numerator, denominator):
    if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
        return pd.NA
    return numerator / denominator


def prepare_premium_claims_summary(data: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if data.empty:
        cols = group_cols + ["primas", "siniestros", "siniestralidad"]
        return pd.DataFrame(columns=cols)

    premiums = (
        data[data["metric_name"] == "gross_written_premium"]
        .groupby(group_cols, as_index=False)["metric_value"]
        .sum()
        .rename(columns={"metric_value": "primas"})
    )

    claims = (
        data[data["metric_name"] == "claims"]
        .groupby(group_cols, as_index=False)["metric_value"]
        .sum()
        .rename(columns={"metric_value": "siniestros"})
    )

    summary = premiums.merge(claims, on=group_cols, how="left")
    summary["siniestros"] = summary["siniestros"].fillna(0)
    summary["siniestralidad"] = summary["siniestros"] / summary["primas"].replace({0: pd.NA})
    return summary


def calculate_company_premium_evolution(company_df: pd.DataFrame) -> pd.DataFrame:
    summary = prepare_premium_claims_summary(company_df, ["year"])
    if summary.empty:
        return summary
    summary = summary.sort_values("year")
    summary["premium_growth"] = summary["primas"].pct_change()
    summary["claims_premiums_change"] = summary["siniestralidad"].diff()
    return summary


def calculate_company_market_position(
    company: str,
    company_summary: pd.DataFrame,
    market_df: pd.DataFrame,
) -> dict:
    if company_summary.empty or market_df.empty:
        return {
            "available": False,
            "latest_year": pd.NA,
            "rank": pd.NA,
            "company_count": 0,
            "company_premium": pd.NA,
            "market_premium": pd.NA,
            "market_share": pd.NA,
            "market_claims_premiums": pd.NA,
            "company_claims_premiums": pd.NA,
            "top_companies": pd.DataFrame(),
        }

    latest_year = int(company_summary["year"].max())
    market_company = prepare_premium_claims_summary(
        market_df[market_df["year"] == latest_year],
        ["company_standard"],
    )
    if market_company.empty:
        return {
            "available": False,
            "latest_year": latest_year,
            "rank": pd.NA,
            "company_count": 0,
            "company_premium": pd.NA,
            "market_premium": pd.NA,
            "market_share": pd.NA,
            "market_claims_premiums": pd.NA,
            "company_claims_premiums": pd.NA,
            "top_companies": pd.DataFrame(),
        }

    market_company = market_company.sort_values("primas", ascending=False).reset_index(drop=True)
    market_company["rank"] = market_company.index + 1
    market_total = market_company["primas"].sum()
    market_claims = market_company["siniestros"].sum()
    market_company["market_share"] = market_company["primas"] / market_total if market_total else pd.NA
    selected_row = market_company[market_company["company_standard"] == company]
    if selected_row.empty:
        selected = {}
    else:
        selected = selected_row.iloc[0].to_dict()

    top_companies = market_company.head(5).copy()
    return {
        "available": bool(selected),
        "latest_year": latest_year,
        "rank": selected.get("rank", pd.NA),
        "company_count": int(market_company["company_standard"].nunique()),
        "company_premium": selected.get("primas", pd.NA),
        "market_premium": market_total,
        "market_share": selected.get("market_share", pd.NA),
        "market_claims_premiums": safe_divide(market_claims, market_total),
        "company_claims_premiums": selected.get("siniestralidad", pd.NA),
        "top_companies": top_companies,
    }


def calculate_company_main_competitors(
    company: str,
    market_df: pd.DataFrame,
    latest_year: int,
    limit: int = 10,
) -> pd.DataFrame:
    if market_df.empty or pd.isna(latest_year):
        return pd.DataFrame()
    competitors = prepare_premium_claims_summary(
        market_df[market_df["year"] == latest_year],
        ["company_standard"],
    )
    if competitors.empty:
        return competitors
    market_total = competitors["primas"].sum()
    selected_premium = competitors.loc[competitors["company_standard"] == company, "primas"].sum()
    competitors["market_share"] = competitors["primas"] / market_total if market_total else pd.NA
    competitors["premium_difference_vs_selected"] = competitors["primas"] - selected_premium
    competitors["is_selected_company"] = competitors["company_standard"] == company
    return competitors.sort_values("primas", ascending=False).head(limit)


def calculate_company_portfolio_mix(
    company_df: pd.DataFrame,
    latest_year: int,
    minimum_premium: float,
    limit: int = 10,
) -> pd.DataFrame:
    if company_df.empty or pd.isna(latest_year):
        return pd.DataFrame()
    line_year = prepare_premium_claims_summary(company_df, ["line_of_business_standard", "year"])
    if line_year.empty:
        return line_year
    line_year = line_year.sort_values(["line_of_business_standard", "year"])
    line_year["premium_growth"] = line_year.groupby("line_of_business_standard")["primas"].pct_change()
    line_year["claims_premiums_change"] = line_year.groupby("line_of_business_standard")["siniestralidad"].diff()
    latest = line_year[line_year["year"] == latest_year].copy()
    latest = latest[latest["primas"] >= minimum_premium]
    if latest.empty:
        return latest
    total = latest["primas"].sum()
    latest["portfolio_share"] = latest["primas"] / total if total else pd.NA
    return latest.sort_values("primas", ascending=False).head(limit)


def portfolio_interpretation(portfolio_mix: pd.DataFrame) -> str:
    if portfolio_mix.empty:
        return "Not enough data available for portfolio interpretation."
    top_line = portfolio_mix.iloc[0]
    top_share = top_line.get("portfolio_share", pd.NA)
    top3_share = portfolio_mix.head(3)["portfolio_share"].sum()
    if pd.notna(top_share) and top_share >= 0.5:
        return (
            f"Concentrated portfolio: {top_line['line_of_business_standard']} represents "
            f"{format_percentage(top_share)} of selected company premium."
        )
    if pd.notna(top3_share) and top3_share >= 0.75:
        return f"Moderately concentrated portfolio: top three lines represent {format_percentage(top3_share)} of selected premium."
    return "Diversified portfolio under the selected filters, with no single line dominating premium."


def calculate_company_growth_signals(portfolio_mix: pd.DataFrame) -> pd.DataFrame:
    if portfolio_mix.empty:
        return pd.DataFrame()
    signals = portfolio_mix[
        portfolio_mix["premium_growth"].notna() | portfolio_mix["claims_premiums_change"].notna()
    ].copy()
    if signals.empty:
        return signals
    signals["growth_signal"] = "Stable / review"
    signals.loc[signals["premium_growth"] >= 0.2, "growth_signal"] = "Strong premium growth"
    signals.loc[signals["premium_growth"] <= -0.1, "growth_signal"] = "Premium contraction"
    signals.loc[
        (signals["premium_growth"] >= 0.2) & (signals["claims_premiums_change"] > 0.05),
        "growth_signal",
    ] = "Growth with worsening Claims / Premiums"
    return signals.sort_values(["premium_growth", "claims_premiums_change"], ascending=False).head(5)


def calculate_company_technical_alerts(
    company: str,
    company_summary: pd.DataFrame,
    market_position: dict,
    portfolio_mix: pd.DataFrame,
    reinsurance_summary: dict | None,
) -> list[dict]:
    alerts: list[dict] = []
    if company_summary.empty:
        return [
            {
                "severity": "Medium",
                "title": "Limited data available",
                "explanation": "The selected filters do not provide enough company records for a full brief.",
                "follow_up": "Confirm whether the selected period, line, or city should be broadened before the meeting.",
            }
        ]

    latest = company_summary.sort_values("year").iloc[-1]
    latest_year = int(latest["year"])
    premium_growth = latest.get("premium_growth", pd.NA)
    company_ratio = latest.get("siniestralidad", pd.NA)
    market_ratio = market_position.get("market_claims_premiums", pd.NA)

    if pd.notna(company_ratio) and pd.notna(market_ratio) and company_ratio > market_ratio + 0.10:
        alerts.append(
            {
                "severity": "High" if company_ratio > market_ratio + 0.20 else "Medium",
                "title": "Claims / Premiums above market",
                "explanation": (
                    f"{company} shows Claims / Premiums of {format_percentage(company_ratio)} versus "
                    f"selected market level of {format_percentage(market_ratio)} in {latest_year}."
                ),
                "follow_up": "Ask which lines or reserving/pricing actions explain the gap versus market.",
            }
        )

    if pd.notna(premium_growth) and premium_growth >= 0.20:
        alerts.append(
            {
                "severity": "Medium",
                "title": "Sharp premium growth",
                "explanation": f"Premium grew {format_percentage(premium_growth)} in the latest available period.",
                "follow_up": "Review whether growth is concentrated in specific lines and whether reinsurance support should adjust.",
            }
        )
    elif pd.notna(premium_growth) and premium_growth <= -0.10:
        alerts.append(
            {
                "severity": "Medium",
                "title": "Premium contraction",
                "explanation": f"Premium declined {format_percentage(premium_growth)} in the latest available period.",
                "follow_up": "Ask whether contraction is portfolio pruning, market pressure, classification change, or lost business.",
            }
        )

    if not portfolio_mix.empty:
        top_line = portfolio_mix.iloc[0]
        top_share = top_line.get("portfolio_share", pd.NA)
        if pd.notna(top_share) and top_share >= 0.45:
            alerts.append(
                {
                    "severity": "Medium",
                    "title": f"High concentration in {top_line['line_of_business_standard']}",
                    "explanation": (
                        f"{top_line['line_of_business_standard']} represents {format_percentage(top_share)} "
                        "of selected company premium."
                    ),
                    "follow_up": "Review whether this line is driving volatility, growth strategy, or reinsurance need.",
                }
            )

        worsening = portfolio_mix[
            (portfolio_mix["claims_premiums_change"].notna())
            & (portfolio_mix["claims_premiums_change"] > 0.10)
        ].sort_values("claims_premiums_change", ascending=False)
        if not worsening.empty:
            row = worsening.iloc[0]
            alerts.append(
                {
                    "severity": "Medium",
                    "title": f"Worsening Claims / Premiums in {row['line_of_business_standard']}",
                    "explanation": (
                        f"Claims / Premiums increased by {format_percentage(row['claims_premiums_change'])} "
                        "versus the prior available year."
                    ),
                    "follow_up": "Ask whether the movement reflects claims frequency/severity, pricing, mix, or source effects.",
                }
            )

    if reinsurance_summary and reinsurance_summary.get("available") and pd.notna(reinsurance_summary.get("cession_ratio")):
        cession = reinsurance_summary.get("cession_ratio")
        if cession >= 0.4:
            alerts.append(
                {
                    "severity": "Low",
                    "title": "High exploratory cession ratio",
                    "explanation": f"Exploratory cession ratio is {format_percentage(cession)} in the available reinsurance source.",
                    "follow_up": "Use as a conversation starter; validate Indicadores de Gestion methodology before formal use.",
                }
            )

    if not alerts:
        alerts.append(
            {
                "severity": "Low",
                "title": "No high-priority automatic alert",
                "explanation": "No threshold-based broker alert was triggered under the selected filters.",
                "follow_up": "Use market position, competitors, and portfolio mix to guide the meeting discussion.",
            }
        )
    return alerts


def calculate_company_reinsurance_signals(
    reinsurance_summary: dict | None,
    reinsurance_wide: pd.DataFrame | None = None,
) -> dict:
    if not reinsurance_summary or not reinsurance_summary.get("available"):
        return {
            "available": False,
            "summary": reinsurance_summary or {},
            "line_signals": pd.DataFrame(),
            "text": "Reinsurance indicators are not available for this selection.",
        }

    line_signals = pd.DataFrame()
    if reinsurance_wide is not None and not reinsurance_wide.empty:
        line_signals = (
            reinsurance_wide.groupby(["line_of_business_standard"], as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                retained_premium=("retained_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
                paid_claims=("paid_claims", "sum"),
            )
        )
        line_signals["cession_ratio"] = line_signals["reinsurance_ceded_premium"] / line_signals["gross_written_premium"].replace({0: pd.NA})
        line_signals["retention_ratio"] = line_signals["retained_premium"] / line_signals["gross_written_premium"].replace({0: pd.NA})
        line_signals = line_signals.sort_values("reinsurance_ceded_premium", ascending=False).head(5)

    text = (
        f"Exploratory reinsurance indicators show cession ratio of "
        f"{format_percentage(reinsurance_summary['cession_ratio'])}, retention ratio of "
        f"{format_percentage(reinsurance_summary['retention_ratio'])}, and ceded premium of "
        f"{format_millions(reinsurance_summary['reinsurance_ceded_premium'])}. "
        "Source remains exploratory pending methodology review."
    )
    return {
        "available": True,
        "summary": reinsurance_summary,
        "line_signals": line_signals,
        "text": text,
    }


def generate_broker_meeting_questions(
    company: str,
    selected_line: str,
    company_summary: pd.DataFrame,
    market_position: dict,
    portfolio_mix: pd.DataFrame,
    technical_alerts: list[dict],
    reinsurance_signals: dict,
) -> list[str]:
    line_scope = "the selected portfolio" if selected_line == "TODOS" else selected_line
    questions = []
    if not portfolio_mix.empty:
        top_line = portfolio_mix.iloc[0]["line_of_business_standard"]
        questions.append(f"What is driving {company}'s premium volume in {top_line}, the largest selected line?")
    else:
        questions.append(f"What is driving {company}'s premium movement in {line_scope}?")

    company_ratio = market_position.get("company_claims_premiums", pd.NA)
    market_ratio = market_position.get("market_claims_premiums", pd.NA)
    if pd.notna(company_ratio) and pd.notna(market_ratio):
        questions.append(
            f"How does {company} interpret Claims / Premiums of {format_percentage(company_ratio)} "
            f"versus the selected market at {format_percentage(market_ratio)}?"
        )
    else:
        questions.append("Is the current Claims / Premiums trend aligned with pricing and underwriting actions?")

    if not portfolio_mix.empty and pd.notna(portfolio_mix.iloc[0].get("portfolio_share", pd.NA)):
        top = portfolio_mix.iloc[0]
        questions.append(
            f"Does the {format_percentage(top['portfolio_share'])} concentration in {top['line_of_business_standard']} "
            "reflect strategic focus, market opportunity, or risk appetite?"
        )

    high_alerts = [alert for alert in technical_alerts if alert.get("severity") in ["High", "Medium"]]
    if high_alerts:
        questions.append(high_alerts[0]["follow_up"])

    if reinsurance_signals.get("available"):
        questions.append("How does the company view reinsurance support for its largest or fastest-moving lines?")
        questions.append("Are retained exposures expected to change in the next renewal cycle?")
    else:
        questions.append("Which lines would benefit most from additional reinsurance benchmarking or capacity discussion?")

    questions.append("What data should be reconciled before using these figures in a formal client or market presentation?")
    return questions[:8]


def _source_period(data: pd.DataFrame) -> dict:
    if data.empty:
        return {
            "source": "Data not available",
            "period": "Data not available",
            "records": 0,
        }

    periods = pd.to_datetime(data["period_date"], errors="coerce")
    sources = sorted(data["source"].dropna().astype(str).unique()) if "source" in data.columns else []
    min_period = periods.min()
    max_period = periods.max()
    return {
        "source": "; ".join(sources) if sources else "Data not available",
        "period": (
            f"{min_period.date()} to {max_period.date()}"
            if pd.notna(min_period) and pd.notna(max_period)
            else "Data not available"
        ),
        "records": len(data),
    }


def _latest_and_previous(summary: pd.DataFrame):
    if summary.empty:
        return None, None
    ordered = summary.sort_values("year")
    latest = ordered.iloc[-1]
    previous = ordered.iloc[-2] if len(ordered) > 1 else None
    return latest, previous


def _main_lines(company_df: pd.DataFrame, latest_year: int, limit: int = 5) -> pd.DataFrame:
    premium = company_df[
        (company_df["metric_name"] == "gross_written_premium")
        & (company_df["year"] == latest_year)
    ]
    return (
        premium.groupby("line_of_business_standard", as_index=False)["metric_value"]
        .sum()
        .rename(columns={"metric_value": "gross_written_premium"})
        .sort_values("gross_written_premium", ascending=False)
        .head(limit)
    )


def _fastest_growing_lines(company_df: pd.DataFrame, minimum_premium: float, limit: int = 5) -> pd.DataFrame:
    line_year = prepare_premium_claims_summary(company_df, ["line_of_business_standard", "year"])
    if line_year.empty:
        return pd.DataFrame()

    line_year = line_year.sort_values(["line_of_business_standard", "year"])
    line_year["premium_growth"] = line_year.groupby("line_of_business_standard")["primas"].pct_change()
    latest_year = line_year["year"].max()
    return (
        line_year[
            (line_year["year"] == latest_year)
            & (line_year["primas"] >= minimum_premium)
            & line_year["premium_growth"].notna()
        ]
        .sort_values("premium_growth", ascending=False)
        .head(limit)
    )


def _deteriorating_loss_ratio_lines(company_df: pd.DataFrame, minimum_premium: float, limit: int = 5) -> pd.DataFrame:
    line_year = prepare_premium_claims_summary(company_df, ["line_of_business_standard", "year"])
    if line_year.empty:
        return pd.DataFrame()

    line_year = line_year.sort_values(["line_of_business_standard", "year"])
    line_year["loss_ratio_change"] = line_year.groupby("line_of_business_standard")["siniestralidad"].diff()
    latest_year = line_year["year"].max()
    return (
        line_year[
            (line_year["year"] == latest_year)
            & (line_year["primas"] >= minimum_premium)
            & line_year["loss_ratio_change"].notna()
        ]
        .sort_values("loss_ratio_change", ascending=False)
        .head(limit)
    )


def summarize_reinsurance(reinsurance_wide: pd.DataFrame) -> dict:
    if reinsurance_wide is None or reinsurance_wide.empty:
        return {
            "available": False,
            "gross_written_premium": pd.NA,
            "retained_premium": pd.NA,
            "reinsurance_ceded_premium": pd.NA,
            "cession_ratio": pd.NA,
            "retention_ratio": pd.NA,
            "paid_claims_ratio": pd.NA,
            "source": "Data not available",
            "period": "Data not available",
        }

    gwp = reinsurance_wide["gross_written_premium"].sum()
    retained = reinsurance_wide["retained_premium"].sum()
    ceded = reinsurance_wide["reinsurance_ceded_premium"].sum()
    paid_claims = reinsurance_wide["paid_claims"].sum()
    period = (
        str(int(reinsurance_wide["year"].max()))
        if "year" in reinsurance_wide.columns and not reinsurance_wide["year"].dropna().empty
        else "2025"
    )

    return {
        "available": True,
        "gross_written_premium": gwp,
        "retained_premium": retained,
        "reinsurance_ceded_premium": ceded,
        "cession_ratio": ceded / gwp if gwp else pd.NA,
        "retention_ratio": retained / gwp if gwp else pd.NA,
        "paid_claims_ratio": paid_claims / gwp if gwp else pd.NA,
        "source": "Fasecolda - Indicadores de Gestion 2025",
        "period": period,
    }


def build_company_brief(
    country: str,
    company: str,
    selected_line: str,
    selected_years: list[int],
    company_df: pd.DataFrame,
    market_df: pd.DataFrame,
    reinsurance_summary: dict | None,
    minimum_premium: float,
    reinsurance_wide: pd.DataFrame | None = None,
) -> dict:
    source = _source_period(company_df)
    company_summary = calculate_company_premium_evolution(company_df)
    market_summary = prepare_premium_claims_summary(market_df, ["year"])

    if company_summary.empty:
        reinsurance_signals = calculate_company_reinsurance_signals(reinsurance_summary, reinsurance_wide)
        alerts = calculate_company_technical_alerts(company, company_summary, {}, pd.DataFrame(), reinsurance_summary)

        return {
            "executive_summary": "Data not available for the selected company and filters.",
            "executive_snapshot": [],
            "market_position": calculate_company_market_position(company, company_summary, market_df),
            "competitors": pd.DataFrame(),
            "premium_evolution": pd.DataFrame(),
            "market_share": pd.DataFrame(),
            "main_lines": pd.DataFrame(),
            "portfolio_mix": pd.DataFrame(),
            "portfolio_interpretation": "Not enough data available for portfolio interpretation.",
            "growth_signals": pd.DataFrame(),
            "fastest_growing_lines": pd.DataFrame(),
            "deteriorating_loss_ratio_lines": pd.DataFrame(),
            "reinsurance_signals": reinsurance_signals,
            "reinsurance_text": reinsurance_signals["text"],
            "alerts": alerts,
            "questions": ["What additional source should be reviewed before the meeting?"],
            "source": source,
            "markdown": "# Company Brief\n\nData not available.",
            "company_brief_context": {},
        }

    company_summary = company_summary.sort_values("year")
    latest, previous = _latest_and_previous(company_summary)
    latest_year = int(latest["year"])
    latest_premium = latest["primas"]
    latest_claims = latest["siniestros"]
    latest_lr = latest["siniestralidad"]
    premium_growth = latest["premium_growth"]

    market_share = company_summary[["year", "primas"]].merge(
        market_summary[["year", "primas"]].rename(columns={"primas": "market_primas"}),
        on="year",
        how="left",
    )
    market_share["market_share"] = market_share["primas"] / market_share["market_primas"].replace({0: pd.NA})

    market_position = calculate_company_market_position(company, company_summary, market_df)
    competitors = calculate_company_main_competitors(company, market_df, latest_year)
    portfolio_mix = calculate_company_portfolio_mix(company_df, latest_year, minimum_premium)
    portfolio_text = portfolio_interpretation(portfolio_mix)
    growth_signals = calculate_company_growth_signals(portfolio_mix)
    main_lines = _main_lines(company_df, latest_year)
    fastest_lines = _fastest_growing_lines(company_df, minimum_premium)
    deteriorating_lines = _deteriorating_loss_ratio_lines(company_df, minimum_premium)
    reinsurance_signals = calculate_company_reinsurance_signals(reinsurance_summary, reinsurance_wide)
    alerts = calculate_company_technical_alerts(
        company,
        company_summary,
        market_position,
        portfolio_mix,
        reinsurance_summary,
    )

    line_scope = "all lines" if selected_line == "TODOS" else selected_line
    years_text = f"{min(selected_years)}-{max(selected_years)}" if selected_years else "selected period"

    top_lines_text = (
        ", ".join(main_lines["line_of_business_standard"].astype(str).head(5).tolist())
        if not main_lines.empty
        else "Data not available"
    )

    executive_summary = (
        f"{company} in {country} wrote {format_millions(latest_premium)} in premiums in {latest_year} "
        f"for {line_scope}, with claims of {format_millions(latest_claims)} and a claims-to-premium ratio of "
        f"{format_percentage(latest_lr)}. Premium growth versus the prior available year was "
        f"{format_percentage(premium_growth)}. Main lines by premium were {top_lines_text}."
    )

    questions = generate_broker_meeting_questions(
        company,
        selected_line,
        company_summary,
        market_position,
        portfolio_mix,
        alerts,
        reinsurance_signals,
    )

    if pd.notna(market_position.get("rank", pd.NA)):
        position_text = f"#{int(market_position['rank'])} of {market_position['company_count']} by premium"
    else:
        position_text = "Not enough data available"
    top_share = portfolio_mix.iloc[0]["portfolio_share"] if not portfolio_mix.empty else pd.NA
    top_line_label = (
        f"{portfolio_mix.iloc[0]['line_of_business_standard']} ({format_percentage(top_share)})"
        if not portfolio_mix.empty
        else "Not enough data available"
    )
    market_ratio = market_position.get("market_claims_premiums", pd.NA)
    ratio_signal = (
        "Above selected market"
        if pd.notna(latest_lr) and pd.notna(market_ratio) and latest_lr > market_ratio
        else "At or below selected market"
        if pd.notna(latest_lr) and pd.notna(market_ratio)
        else "Not enough data available"
    )
    broker_angle = (
        questions[0]
        if questions
        else "Review premium movement, Claims / Premiums, portfolio mix and reinsurance needs."
    )
    executive_snapshot = [
        {"label": "Selected year", "value": str(latest_year), "detail": "Latest available year in current filters"},
        {"label": "Premium", "value": format_millions(latest_premium), "detail": "Company premium in selected market"},
        {"label": "Market position", "value": position_text, "detail": "Rank by premium in selected market"},
        {"label": "Market share", "value": format_percentage(market_position.get("market_share", pd.NA)), "detail": "Company premium / selected market premium"},
        {"label": "Portfolio focus", "value": top_line_label, "detail": "Largest selected line by premium"},
        {"label": "Recent growth", "value": format_percentage(premium_growth), "detail": "Premium growth vs prior available year"},
        {"label": "Claims / Premiums", "value": format_percentage(latest_lr), "detail": ratio_signal},
        {"label": "Broker angle", "value": "Review", "detail": broker_angle},
    ]

    markdown = render_company_brief_markdown(
        country=country,
        company=company,
        selected_line=selected_line,
        selected_years=selected_years,
        executive_summary=executive_summary,
        company_summary=company_summary,
        market_share=market_share,
        main_lines=main_lines,
        fastest_lines=fastest_lines,
        deteriorating_lines=deteriorating_lines,
        reinsurance_text=reinsurance_signals["text"],
        alerts=alerts,
        questions=questions,
        source=source,
        market_position=market_position,
        competitors=competitors,
        portfolio_mix=portfolio_mix,
        portfolio_interpretation_text=portfolio_text,
    )

    company_brief_context = {
        "executive_snapshot": executive_snapshot,
        "market_position": market_position,
        "competitors": competitors,
        "portfolio_mix": portfolio_mix,
        "technical_alerts": alerts,
        "reinsurance_signals": reinsurance_signals,
        "broker_questions": questions,
    }

    return {
        "executive_summary": executive_summary,
        "executive_snapshot": executive_snapshot,
        "market_position": market_position,
        "competitors": competitors,
        "premium_evolution": company_summary,
        "market_share": market_share,
        "main_lines": main_lines,
        "portfolio_mix": portfolio_mix,
        "portfolio_interpretation": portfolio_text,
        "growth_signals": growth_signals,
        "fastest_growing_lines": fastest_lines,
        "deteriorating_loss_ratio_lines": deteriorating_lines,
        "reinsurance_signals": reinsurance_signals,
        "reinsurance_text": reinsurance_signals["text"],
        "alerts": alerts,
        "questions": questions,
        "source": source,
        "markdown": markdown,
        "company_brief_context": company_brief_context,
    }


def _markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 10) -> str:
    if df is None or df.empty:
        return "Data not available.\n"
    available_columns = [column for column in columns if column in df.columns]
    if not available_columns:
        return "Data not available.\n"
    display = df[available_columns].head(limit).copy()
    display = display.rename(columns=DISPLAY_COLUMN_NAMES)
    header = "| " + " | ".join(display.columns.astype(str)) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = []
    for _, row in display.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in display.columns) + " |")
    return "\n".join([header, separator] + rows)


def _alert_markdown(alerts: list[dict]) -> str:
    if not alerts:
        return "- No automatic alert triggered."
    lines = []
    for alert in alerts:
        if isinstance(alert, dict):
            lines.append(
                f"- [{alert.get('severity', 'Review')}] {alert.get('title', 'Alert')}: "
                f"{alert.get('explanation', '')} Follow-up: {alert.get('follow_up', '')}"
            )
        else:
            lines.append(f"- {alert}")
    return "\n".join(lines)


def render_company_brief_markdown(
    country,
    company,
    selected_line,
    selected_years,
    executive_summary,
    company_summary,
    market_share,
    main_lines,
    fastest_lines,
    deteriorating_lines,
    reinsurance_text,
    alerts,
    questions,
    source,
    market_position=None,
    competitors=None,
    portfolio_mix=None,
    portfolio_interpretation_text="",
) -> str:
    year_scope = f"{min(selected_years)}-{max(selected_years)}" if selected_years else "selected period"
    line_scope = "All lines" if selected_line == "TODOS" else selected_line

    return f"""# Company Brief: {company}

## Scope
- Country: {country}
- Company: {company}
- Line of business: {line_scope}
- Years: {year_scope}

## Executive Summary
{executive_summary}

## Market Position
- Rank: {market_position.get("rank", "N/A") if market_position else "N/A"}
- Market share: {format_percentage(market_position.get("market_share", pd.NA)) if market_position else "N/A"}
- Market premium: {format_millions(market_position.get("market_premium", pd.NA)) if market_position else "N/A"}

## Main Competitors
{_markdown_table(competitors, ["company_standard", "rank", "primas", "market_share", "siniestralidad", "premium_difference_vs_selected"]) if competitors is not None else "Data not available."}

## Premium Evolution
{_markdown_table(company_summary, ["year", "primas", "siniestros", "siniestralidad", "premium_growth"])}

## Claims / Premiums Evolution
Claims / Premiums is an analytical ratio calculated as claims divided by gross written premium. It is not necessarily Fasecolda's official technical loss ratio, technical siniestralidad, or combined ratio.

## Market Share
{_markdown_table(market_share, ["year", "primas", "market_primas", "market_share"])}

## Main Lines of Business
{_markdown_table(portfolio_mix, ["line_of_business_standard", "primas", "portfolio_share", "siniestralidad", "premium_growth"]) if portfolio_mix is not None else _markdown_table(main_lines, ["line_of_business_standard", "gross_written_premium"])}

Portfolio interpretation: {portfolio_interpretation_text}

## Fastest Growing Lines
{_markdown_table(fastest_lines, ["line_of_business_standard", "year", "primas", "premium_growth"])}

## Lines With Deteriorating Claims / Premiums
{_markdown_table(deteriorating_lines, ["line_of_business_standard", "year", "siniestralidad", "loss_ratio_change"])}

## Reinsurance Indicators
{reinsurance_text}

## Key Alerts
{_alert_markdown(alerts)}

## Suggested Meeting Questions
{chr(10).join(f"- {question}" for question in questions)}

## Data Source And Period Used
- Source: {source["source"]}
- Period: {source["period"]}
- Records used: {source["records"]:,}
- Generated at: {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Methodology Notes
- Gross written premium and claims come from Fasecolda - Ciudades y Ramos.
- Market share is calculated against the filtered market reference.
- Reinsurance indicators come from Fasecolda - Indicadores de Gestion 2025 when available and remain exploratory.
- 2026 YTD should not be compared directly against full-year 2025 without a period warning.
"""


def render_one_pager_markdown(brief: dict, company: str, country: str) -> str:
    latest = brief["premium_evolution"].sort_values("year").tail(1)
    if latest.empty:
        kpi_text = "Data not available."
    else:
        row = latest.iloc[0]
        kpi_text = (
            f"- Premiums: {format_millions(row['primas'])}\n"
            f"- Claims: {format_millions(row['siniestros'])}\n"
            f"- Claims / Premiums: {format_percentage(row['siniestralidad'])}\n"
            f"- Premium growth: {format_percentage(row['premium_growth'])}"
        )

    return f"""# One-Pager: {company} ({country})

## Key KPIs
{kpi_text}

## Top Lines Of Business
{_markdown_table(brief["main_lines"], ["line_of_business_standard", "gross_written_premium"], limit=5)}

## Reinsurance Metrics
{brief.get("reinsurance_text", "Data not available.")}

## Technical Alerts
{_alert_markdown(brief["alerts"])}

## Suggested Discussion Points
{chr(10).join(f"- {question}" for question in brief["questions"][:5])}

## Methodology Notes
- This one-pager is generated from structured public data loaded in DuckDB.
- It is intended for broker meeting preparation, not legal or financial advice.
- Indicadores de Gestion 2025 remains exploratory pending methodology review.
"""


def render_markdown_as_html(markdown_text: str, title: str) -> str:
    body = []
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body.append(f"<li>{escape(line[2:])}</li>")
        elif line.strip() == "":
            body.append("")
        else:
            body.append(f"<p>{escape(line)}</p>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{escape(title)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    h1 {{ color: #0f172a; }}
    h2 {{ border-bottom: 1px solid #d8dee9; padding-bottom: 4px; margin-top: 28px; }}
    p, li {{ font-size: 14px; line-height: 1.45; }}
  </style>
</head>
<body>
{chr(10).join(body)}
</body>
</html>"""


def build_reinsurance_wide(indicadores_df: pd.DataFrame, country: str, company: str | None = None, line: str | None = None) -> pd.DataFrame:
    if indicadores_df is None or indicadores_df.empty:
        return pd.DataFrame()

    data = indicadores_df[indicadores_df["country"] == country].copy()
    if company:
        data = data[data["company_standard"].astype(str).str.upper() == str(company).strip().upper()]
    if line:
        data = data[data["line_of_business_standard"].astype(str).str.upper() == str(line).strip().upper()]

    if data.empty:
        return pd.DataFrame()

    wide = (
        data.pivot_table(
            index=["country", "year", "company_standard", "line_of_business_standard"],
            columns="metric_name",
            values="metric_value",
            aggfunc="sum",
        )
        .reset_index()
    )
    wide.columns.name = None
    for col in [
        "gross_written_premium",
        "retained_premium",
        "reinsurance_ceded_premium",
        "paid_claims",
    ]:
        if col not in wide.columns:
            wide[col] = 0.0
        wide[col] = pd.to_numeric(wide[col], errors="coerce").fillna(0)
    return wide


def aggregate_reinsurance_metrics(reinsurance_wide: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if reinsurance_wide is None or reinsurance_wide.empty:
        return pd.DataFrame()
    required = [
        "gross_written_premium",
        "retained_premium",
        "reinsurance_ceded_premium",
        "paid_claims",
    ]
    data = reinsurance_wide.copy()
    for column in required:
        if column not in data.columns:
            data[column] = 0.0
        data[column] = pd.to_numeric(data[column], errors="coerce").fillna(0.0)

    summary = (
        data.groupby(group_cols, as_index=False)
        .agg(
            gross_written_premium=("gross_written_premium", "sum"),
            retained_premium=("retained_premium", "sum"),
            reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
            paid_claims=("paid_claims", "sum"),
            companies=("company_standard", "nunique") if "company_standard" in data.columns else ("gross_written_premium", "size"),
            lines=("line_of_business_standard", "nunique") if "line_of_business_standard" in data.columns else ("gross_written_premium", "size"),
        )
    )
    summary["cession_ratio"] = summary["reinsurance_ceded_premium"] / summary["gross_written_premium"].replace({0: pd.NA})
    summary["retention_ratio"] = summary["retained_premium"] / summary["gross_written_premium"].replace({0: pd.NA})
    summary["paid_claims_ratio"] = summary["paid_claims"] / summary["gross_written_premium"].replace({0: pd.NA})
    return summary


def build_reinsurance_executive_snapshot(
    selected_summary: dict,
    market_benchmark: dict,
    by_line: pd.DataFrame,
    selected_company: str,
) -> list[dict]:
    if not selected_summary.get("available"):
        return []
    market_gap = market_benchmark.get("cession_ratio_difference")
    gap_text = (
        f"{market_gap:+.1%} vs market"
        if pd.notna(market_gap)
        else "Market benchmark not available"
    )
    main_line = "Not enough data available"
    if by_line is not None and not by_line.empty:
        top = by_line.sort_values("reinsurance_ceded_premium", ascending=False).iloc[0]
        share = top.get("ceded_share", pd.NA)
        main_line = f"{top['line_of_business_standard']} ({format_percentage(share)})"
    company_label = "Market" if selected_company == "TODAS" else selected_company
    broker_angle = (
        "Review ceded structure versus market and concentration in most ceded lines."
        if selected_company != "TODAS"
        else "Use market cession patterns to identify treaty discussion opportunities by line."
    )
    return [
        {"label": "Scope", "value": company_label, "detail": "Selected reinsurance view"},
        {"label": "Latest year", "value": str(selected_summary.get("period", "N/A")), "detail": "Available source period"},
        {"label": "Emitted premium", "value": format_millions(selected_summary.get("gross_written_premium", pd.NA)), "detail": "Source gross/emitted premium"},
        {"label": "Ceded premium", "value": format_millions(selected_summary.get("reinsurance_ceded_premium", pd.NA)), "detail": "Premium ceded to reinsurance"},
        {"label": "Cession ratio", "value": format_percentage(selected_summary.get("cession_ratio", pd.NA)), "detail": gap_text},
        {"label": "Retention ratio", "value": format_percentage(selected_summary.get("retention_ratio", pd.NA)), "detail": "Retained premium / emitted premium"},
        {"label": "Paid claims", "value": format_millions(selected_summary.get("paid_claims", pd.NA)), "detail": "Paid claims from exploratory source"},
        {"label": "Main ceded line", "value": main_line, "detail": broker_angle},
    ]


def calculate_reinsurance_market_benchmark(
    selected_wide: pd.DataFrame,
    market_wide: pd.DataFrame,
    selected_company: str,
) -> dict:
    selected_summary = summarize_reinsurance(selected_wide)
    market_summary = summarize_reinsurance(market_wide)
    result = {
        "selected": selected_summary,
        "market": market_summary,
        "cession_ratio_difference": pd.NA,
        "retention_ratio_difference": pd.NA,
        "available": selected_summary.get("available", False) and market_summary.get("available", False),
    }
    if result["available"] and selected_company != "TODAS":
        result["cession_ratio_difference"] = selected_summary["cession_ratio"] - market_summary["cession_ratio"]
        result["retention_ratio_difference"] = selected_summary["retention_ratio"] - market_summary["retention_ratio"]
    return result


def calculate_reinsurance_by_line(reinsurance_wide: pd.DataFrame, minimum_premium: float = 0) -> pd.DataFrame:
    by_line = aggregate_reinsurance_metrics(reinsurance_wide, ["line_of_business_standard"])
    if by_line.empty:
        return by_line
    by_line = by_line[by_line["gross_written_premium"] >= minimum_premium].copy()
    total_ceded = by_line["reinsurance_ceded_premium"].sum()
    by_line["ceded_share"] = by_line["reinsurance_ceded_premium"] / total_ceded if total_ceded else pd.NA
    return by_line.sort_values("reinsurance_ceded_premium", ascending=False)


def calculate_reinsurance_evolution(reinsurance_wide: pd.DataFrame) -> pd.DataFrame:
    evolution = aggregate_reinsurance_metrics(reinsurance_wide, ["year"])
    if evolution.empty:
        return evolution
    evolution = evolution.sort_values("year")
    evolution["ceded_premium_growth"] = evolution["reinsurance_ceded_premium"].pct_change()
    evolution["retained_premium_growth"] = evolution["retained_premium"].pct_change()
    evolution["cession_ratio_change"] = evolution["cession_ratio"].diff()
    evolution["retention_ratio_change"] = evolution["retention_ratio"].diff()
    return evolution


def calculate_reinsurance_signals(
    selected_company: str,
    selected_summary: dict,
    market_benchmark: dict,
    by_line: pd.DataFrame,
    evolution: pd.DataFrame,
) -> list[dict]:
    signals: list[dict] = []
    cession_ratio = selected_summary.get("cession_ratio", pd.NA)
    retention_ratio = selected_summary.get("retention_ratio", pd.NA)
    gap = market_benchmark.get("cession_ratio_difference", pd.NA)

    if pd.notna(gap) and abs(gap) >= 0.10:
        signals.append(
            {
                "severity": "Medium",
                "title": "Cession behavior differs from market",
                "explanation": (
                    f"Selected company cession ratio is {format_percentage(gap)} "
                    "different from the selected market benchmark."
                ),
                "follow_up": "Discuss whether retention appetite, treaty structure or line mix explains the difference.",
            }
        )
    if pd.notna(cession_ratio) and cession_ratio >= 0.45:
        signals.append(
            {
                "severity": "Medium",
                "title": "High cession ratio",
                "explanation": f"Cession ratio is {format_percentage(cession_ratio)} in the selected scope.",
                "follow_up": "Review whether ceded structure remains aligned with growth, volatility and capacity needs.",
            }
        )
    if pd.notna(retention_ratio) and retention_ratio >= 0.80:
        signals.append(
            {
                "severity": "Low",
                "title": "High retention ratio",
                "explanation": f"Retention ratio is {format_percentage(retention_ratio)} in the selected scope.",
                "follow_up": "Ask whether retained exposure is intentional and aligned with risk appetite.",
            }
        )

    if by_line is not None and not by_line.empty:
        top = by_line.iloc[0]
        if pd.notna(top.get("ceded_share", pd.NA)) and top["ceded_share"] >= 0.35:
            signals.append(
                {
                    "severity": "Medium",
                    "title": f"Ceded premium concentration in {top['line_of_business_standard']}",
                    "explanation": (
                        f"{top['line_of_business_standard']} represents {format_percentage(top['ceded_share'])} "
                        "of selected ceded premium."
                    ),
                    "follow_up": "Review whether treaty capacity and terms are driven by this line.",
                }
            )
        high_paid = by_line[
            by_line["paid_claims_ratio"].notna() & (by_line["paid_claims_ratio"] >= 0.7)
        ].sort_values("paid_claims_ratio", ascending=False)
        if not high_paid.empty:
            row = high_paid.iloc[0]
            signals.append(
                {
                    "severity": "Medium",
                    "title": f"High paid claims / premium in {row['line_of_business_standard']}",
                    "explanation": (
                        f"Paid claims / emitted premium is {format_percentage(row['paid_claims_ratio'])} "
                        "for this line in the exploratory source."
                    ),
                    "follow_up": "Use as a discussion prompt; validate source methodology before formal conclusions.",
                }
            )

    if evolution is not None and len(evolution) > 1:
        latest = evolution.sort_values("year").iloc[-1]
        if pd.notna(latest.get("cession_ratio_change", pd.NA)) and abs(latest["cession_ratio_change"]) >= 0.10:
            signals.append(
                {
                    "severity": "Medium",
                    "title": "Material cession ratio change",
                    "explanation": (
                        f"Cession ratio changed by {format_percentage(latest['cession_ratio_change'])} "
                        "versus the prior available year."
                    ),
                    "follow_up": "Ask whether this reflects treaty structure, portfolio mix, pricing or capacity conditions.",
                }
            )

    if not signals:
        signals.append(
            {
                "severity": "Low",
                "title": "No high-priority reinsurance signal",
                "explanation": "No threshold-based treaty signal was triggered under the selected filters.",
                "follow_up": "Use benchmark and line tables to guide the reinsurance discussion.",
            }
        )
    return signals


def generate_reinsurance_broker_questions(
    selected_company: str,
    selected_line: str,
    by_line: pd.DataFrame,
    signals: list[dict],
    market_benchmark: dict,
) -> list[str]:
    company_scope = "the market" if selected_company == "TODAS" else selected_company
    line_scope = "the selected portfolio" if selected_line == "TODOS" else selected_line
    questions = []
    if by_line is not None and not by_line.empty:
        top_line = by_line.iloc[0]["line_of_business_standard"]
        questions.append(f"What explains the ceded premium concentration in {top_line} for {company_scope}?")
    else:
        questions.append(f"What reinsurance structure is most relevant for {company_scope} in {line_scope}?")

    gap = market_benchmark.get("cession_ratio_difference", pd.NA)
    if pd.notna(gap):
        questions.append(
            f"Why is the selected cession ratio {format_percentage(gap)} different from the selected market benchmark?"
        )
    else:
        questions.append("Is the current cession and retention balance aligned with risk appetite and growth plans?")

    material_signal = next((signal for signal in signals if signal.get("severity") in ["High", "Medium"]), None)
    if material_signal:
        questions.append(material_signal["follow_up"])

    questions.extend(
        [
            "Are there lines where the company expects to retain more or less risk in the next renewal?",
            "How does the company view market capacity for its most ceded lines?",
            "Are treaty structures, limits, retentions or reinstatements expected to change?",
            "Which source figures should be reconciled before using this analysis in a formal placement discussion?",
        ]
    )
    return questions[:8]


def build_reinsurance_view_context(
    selected_wide: pd.DataFrame,
    market_wide: pd.DataFrame,
    selected_company: str,
    selected_line: str,
    minimum_premium: float,
) -> dict:
    selected_summary = summarize_reinsurance(selected_wide)
    market_benchmark = calculate_reinsurance_market_benchmark(selected_wide, market_wide, selected_company)
    by_line = calculate_reinsurance_by_line(selected_wide, minimum_premium)
    evolution = calculate_reinsurance_evolution(selected_wide)
    signals = calculate_reinsurance_signals(
        selected_company,
        selected_summary,
        market_benchmark,
        by_line,
        evolution,
    )
    questions = generate_reinsurance_broker_questions(
        selected_company,
        selected_line,
        by_line,
        signals,
        market_benchmark,
    )
    snapshot = build_reinsurance_executive_snapshot(
        selected_summary,
        market_benchmark,
        by_line,
        selected_company,
    )
    return {
        "available": selected_summary.get("available", False),
        "executive_snapshot": snapshot,
        "selected_summary": selected_summary,
        "market_benchmark": market_benchmark,
        "by_line": by_line,
        "evolution": evolution,
        "signals": signals,
        "broker_questions": questions,
        "reinsurance_brief_context": {
            "executive_snapshot": snapshot,
            "company_vs_market": market_benchmark,
            "by_line": by_line,
            "evolution": evolution,
            "signals": signals,
            "broker_questions": questions,
        },
    }


def build_technical_signals(
    market_df: pd.DataFrame,
    indicadores_df: pd.DataFrame,
    country: str,
    latest_year: int,
    minimum_premium: float,
) -> pd.DataFrame:
    signals = []

    def add_signal(signal_type, metric_value, year, company, line, explanation, source):
        signals.append(
            {
                "signal_type": signal_type,
                "metric_value": metric_value,
                "year": year,
                "company": company,
                "line_of_business": line,
                "explanation": explanation,
                "source": source,
            }
        )

    company_year = prepare_premium_claims_summary(market_df, ["company_standard", "year"])
    if not company_year.empty:
        company_year = company_year.sort_values(["company_standard", "year"])
        company_year["premium_growth"] = company_year.groupby("company_standard")["primas"].pct_change()
        for _, row in (
            company_year[
                (company_year["year"] == latest_year)
                & (company_year["primas"] >= minimum_premium)
                & company_year["premium_growth"].notna()
            ]
            .sort_values("premium_growth", ascending=False)
            .head(10)
            .iterrows()
        ):
            add_signal(
                "Highest premium growth companies",
                row["premium_growth"],
                row["year"],
                row["company_standard"],
                "All selected lines",
                "Company premium growth versus prior available year.",
                "Fasecolda - Ciudades y Ramos",
            )

        for _, row in (
            company_year[
                (company_year["year"] == latest_year)
                & (company_year["primas"] >= minimum_premium)
            ]
            .sort_values("siniestralidad", ascending=False)
            .head(10)
            .iterrows()
        ):
            add_signal(
                "Highest claims-to-premium companies",
                row["siniestralidad"],
                row["year"],
                row["company_standard"],
                "All selected lines",
                "Company analytical claims-to-premium ratio is among the highest under current filters.",
                "Fasecolda - Ciudades y Ramos",
            )

    market_total = (
        company_year.groupby("year", as_index=False)["primas"].sum().rename(columns={"primas": "market_primas"})
        if not company_year.empty
        else pd.DataFrame()
    )
    if not company_year.empty and not market_total.empty:
        share = company_year.merge(market_total, on="year", how="left")
        share["market_share"] = share["primas"] / share["market_primas"].replace({0: pd.NA})
        share = share.sort_values(["company_standard", "year"])
        share["market_share_change"] = share.groupby("company_standard")["market_share"].diff()
        latest_share = share[
            (share["year"] == latest_year)
            & (share["primas"] >= minimum_premium)
            & share["market_share_change"].notna()
        ]
        for signal_type, ascending in [
            ("Companies gaining market share", False),
            ("Companies losing market share", True),
        ]:
            for _, row in latest_share.sort_values("market_share_change", ascending=ascending).head(10).iterrows():
                add_signal(
                    signal_type,
                    row["market_share_change"],
                    row["year"],
                    row["company_standard"],
                    "All selected lines",
                    "Market share movement versus prior available year within current filters.",
                    "Fasecolda - Ciudades y Ramos",
                )

    line_year = prepare_premium_claims_summary(market_df, ["line_of_business_standard", "year"])
    if not line_year.empty:
        line_year = line_year.sort_values(["line_of_business_standard", "year"])
        line_year["loss_ratio_change"] = line_year.groupby("line_of_business_standard")["siniestralidad"].diff()
        for _, row in (
            line_year[
                (line_year["year"] == latest_year)
                & (line_year["primas"] >= minimum_premium)
                & line_year["loss_ratio_change"].notna()
            ]
            .sort_values("loss_ratio_change", ascending=False)
            .head(10)
            .iterrows()
        ):
            add_signal(
                "Lines with increasing claims-to-premium ratio",
                row["loss_ratio_change"],
                row["year"],
                "Market",
                row["line_of_business_standard"],
                "Analytical claims-to-premium ratio increased versus prior available year.",
                "Fasecolda - Ciudades y Ramos",
            )

    re_wide = build_reinsurance_wide(indicadores_df, country)
    if not re_wide.empty:
        line_re = (
            re_wide.groupby(["year", "line_of_business_standard"], as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
            )
        )
        line_re["cession_ratio"] = line_re["reinsurance_ceded_premium"] / line_re["gross_written_premium"].replace({0: pd.NA})
        for _, row in line_re.dropna(subset=["cession_ratio"]).sort_values("cession_ratio", ascending=False).head(10).iterrows():
            add_signal(
                "Lines with high reinsurance cession ratio",
                row["cession_ratio"],
                row["year"],
                "Market",
                row["line_of_business_standard"],
                "Exploratory cession ratio is high relative to other lines.",
                "Fasecolda - Indicadores de Gestion 2025",
            )

        company_re = (
            re_wide.groupby(["year", "company_standard"], as_index=False)
            .agg(
                gross_written_premium=("gross_written_premium", "sum"),
                reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
            )
        )
        company_re["cession_ratio"] = company_re["reinsurance_ceded_premium"] / company_re["gross_written_premium"].replace({0: pd.NA})
        for _, row in company_re.dropna(subset=["cession_ratio"]).sort_values("cession_ratio", ascending=False).head(10).iterrows():
            add_signal(
                "Companies with high cession ratio",
                row["cession_ratio"],
                row["year"],
                row["company_standard"],
                "All Indicadores lines",
                "Exploratory cession ratio may indicate placement or retention review angle.",
                "Fasecolda - Indicadores de Gestion 2025",
            )

    signal_df = pd.DataFrame(signals)
    if signal_df.empty:
        return signal_df

    watchlist = signal_df[
        signal_df["signal_type"].isin(
            [
                "Highest claims-to-premium companies",
                "Companies losing market share",
                "Lines with increasing claims-to-premium ratio",
                "Companies with high cession ratio",
            ]
        )
    ].copy()
    watchlist["signal_type"] = "Broker watchlist"
    watchlist["explanation"] = "Broker-relevant watchlist item for meeting preparation."

    return pd.concat([signal_df, watchlist.head(20)], ignore_index=True)


def annual_summary_csv(filtered_df: pd.DataFrame) -> str:
    summary = prepare_premium_claims_summary(filtered_df, ["year"])
    if not summary.empty:
        summary = summary.sort_values("year")
        summary["premium_growth"] = summary["primas"].pct_change()
    return summary.to_csv(index=False, encoding="utf-8-sig")


def company_summary_csv(filtered_df: pd.DataFrame) -> str:
    summary = prepare_premium_claims_summary(filtered_df, ["company_standard", "year"])
    if not summary.empty:
        summary = summary.sort_values(["company_standard", "year"])
        summary["premium_growth"] = summary.groupby("company_standard")["primas"].pct_change()
    return summary.to_csv(index=False, encoding="utf-8-sig")


def reinsurance_summary_csv(indicadores_df: pd.DataFrame, country: str) -> str:
    re_wide = build_reinsurance_wide(indicadores_df, country)
    if re_wide.empty:
        return pd.DataFrame().to_csv(index=False, encoding="utf-8-sig")
    summary = (
        re_wide.groupby(["year", "company_standard", "line_of_business_standard"], as_index=False)
        .agg(
            gross_written_premium=("gross_written_premium", "sum"),
            retained_premium=("retained_premium", "sum"),
            reinsurance_ceded_premium=("reinsurance_ceded_premium", "sum"),
            paid_claims=("paid_claims", "sum"),
        )
    )
    summary["reinsurance_cession_ratio"] = summary["reinsurance_ceded_premium"] / summary["gross_written_premium"].replace({0: pd.NA})
    summary["retention_ratio"] = summary["retained_premium"] / summary["gross_written_premium"].replace({0: pd.NA})
    return summary.to_csv(index=False, encoding="utf-8-sig")
