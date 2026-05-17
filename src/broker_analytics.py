from __future__ import annotations

from datetime import datetime
from html import escape

import pandas as pd


def format_millions(value):
    if pd.isna(value):
        return "N/A"
    return f"COP {value / 1_000_000:,.0f} MM"


def format_percentage(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


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
) -> dict:
    source = _source_period(company_df)
    company_summary = prepare_premium_claims_summary(company_df, ["year"])
    market_summary = prepare_premium_claims_summary(market_df, ["year"])

    if company_summary.empty:
        reinsurance_text = "Reinsurance indicators are not available for the selected filters."
        if reinsurance_summary and reinsurance_summary.get("available"):
            reinsurance_text = (
                f"Exploratory reinsurance indicators show cession ratio of "
                f"{format_percentage(reinsurance_summary['cession_ratio'])}, retention ratio of "
                f"{format_percentage(reinsurance_summary['retention_ratio'])}, and ceded premium of "
                f"{format_millions(reinsurance_summary['reinsurance_ceded_premium'])}. "
                "Source remains exploratory pending methodology review."
            )

        return {
            "executive_summary": "Data not available for the selected company and filters.",
            "premium_evolution": pd.DataFrame(),
            "market_share": pd.DataFrame(),
            "main_lines": pd.DataFrame(),
            "fastest_growing_lines": pd.DataFrame(),
            "deteriorating_loss_ratio_lines": pd.DataFrame(),
            "reinsurance_text": reinsurance_text,
            "alerts": ["Data not available for the selected company and filters."],
            "questions": ["What additional source should be reviewed before the meeting?"],
            "source": source,
            "markdown": "# Company Brief\n\nData not available.",
        }

    company_summary = company_summary.sort_values("year")
    company_summary["premium_growth"] = company_summary["primas"].pct_change()
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

    main_lines = _main_lines(company_df, latest_year)
    fastest_lines = _fastest_growing_lines(company_df, minimum_premium)
    deteriorating_lines = _deteriorating_loss_ratio_lines(company_df, minimum_premium)

    alerts = []
    if pd.notna(latest_lr) and latest_lr >= 0.7:
        alerts.append(f"High loss ratio in {latest_year}: {format_percentage(latest_lr)}.")
    if pd.notna(premium_growth) and premium_growth < -0.05:
        alerts.append(f"Premium contraction in {latest_year}: {format_percentage(premium_growth)}.")
    if not deteriorating_lines.empty:
        top_deteriorating = deteriorating_lines.iloc[0]
        alerts.append(
            f"Loss ratio deterioration in {top_deteriorating['line_of_business_standard']}: "
            f"{format_percentage(top_deteriorating['loss_ratio_change'])} change vs prior year."
        )
    if reinsurance_summary and reinsurance_summary.get("available") and pd.notna(reinsurance_summary.get("cession_ratio")):
        if reinsurance_summary["cession_ratio"] >= 0.4:
            alerts.append(
                f"High exploratory reinsurance cession ratio: {format_percentage(reinsurance_summary['cession_ratio'])}."
            )
    if not alerts:
        alerts.append("No automatic high-priority alert triggered under current thresholds.")

    line_scope = "all lines" if selected_line == "TODOS" else selected_line
    years_text = f"{min(selected_years)}-{max(selected_years)}" if selected_years else "selected period"

    top_lines_text = (
        ", ".join(main_lines["line_of_business_standard"].astype(str).head(5).tolist())
        if not main_lines.empty
        else "Data not available"
    )

    executive_summary = (
        f"{company} in {country} wrote {format_millions(latest_premium)} in premiums in {latest_year} "
        f"for {line_scope}, with claims of {format_millions(latest_claims)} and a loss ratio of "
        f"{format_percentage(latest_lr)}. Premium growth versus the prior available year was "
        f"{format_percentage(premium_growth)}. Main lines by premium were {top_lines_text}."
    )

    reinsurance_text = "Reinsurance indicators are not available for the selected filters."
    if reinsurance_summary and reinsurance_summary.get("available"):
        reinsurance_text = (
            f"Exploratory reinsurance indicators show cession ratio of "
            f"{format_percentage(reinsurance_summary['cession_ratio'])}, retention ratio of "
            f"{format_percentage(reinsurance_summary['retention_ratio'])}, and ceded premium of "
            f"{format_millions(reinsurance_summary['reinsurance_ceded_premium'])}. "
            "Source remains exploratory pending methodology review."
        )

    questions = [
        f"What explains {company}'s premium movement in {line_scope} during {years_text}?",
        "Which portfolios are driving loss ratio pressure, and what underwriting actions are planned?",
        "Where could reinsurance structure, limits, retentions, or reinstatement terms be reviewed?",
        "Are growth targets aligned with technical pricing and risk selection?",
        "What market intelligence would be most useful before renewal or placement discussions?",
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
        reinsurance_text=reinsurance_text,
        alerts=alerts,
        questions=questions,
        source=source,
    )

    return {
        "executive_summary": executive_summary,
        "premium_evolution": company_summary,
        "market_share": market_share,
        "main_lines": main_lines,
        "fastest_growing_lines": fastest_lines,
        "deteriorating_loss_ratio_lines": deteriorating_lines,
        "reinsurance_text": reinsurance_text,
        "alerts": alerts,
        "questions": questions,
        "source": source,
        "markdown": markdown,
    }


def _markdown_table(df: pd.DataFrame, columns: list[str], limit: int = 10) -> str:
    if df is None or df.empty:
        return "Data not available.\n"
    display = df[columns].head(limit).copy()
    header = "| " + " | ".join(display.columns.astype(str)) + " |"
    separator = "| " + " | ".join(["---"] * len(display.columns)) + " |"
    rows = []
    for _, row in display.iterrows():
        rows.append("| " + " | ".join(str(row[col]) for col in display.columns) + " |")
    return "\n".join([header, separator] + rows)


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

## Premium Evolution
{_markdown_table(company_summary, ["year", "primas", "siniestros", "siniestralidad", "premium_growth"])}

## Claims / Loss Ratio Evolution
Loss ratio is calculated as claims divided by gross written premium.

## Market Share
{_markdown_table(market_share, ["year", "primas", "market_primas", "market_share"])}

## Main Lines of Business
{_markdown_table(main_lines, ["line_of_business_standard", "gross_written_premium"])}

## Fastest Growing Lines
{_markdown_table(fastest_lines, ["line_of_business_standard", "year", "primas", "premium_growth"])}

## Lines With Deteriorating Loss Ratio
{_markdown_table(deteriorating_lines, ["line_of_business_standard", "year", "siniestralidad", "loss_ratio_change"])}

## Reinsurance Indicators
{reinsurance_text}

## Key Alerts
{chr(10).join(f"- {alert}" for alert in alerts)}

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
            f"- Loss ratio: {format_percentage(row['siniestralidad'])}\n"
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
{chr(10).join(f"- {alert}" for alert in brief["alerts"])}

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
                "Highest loss ratio companies",
                row["siniestralidad"],
                row["year"],
                row["company_standard"],
                "All selected lines",
                "Company loss ratio is among the highest under current filters.",
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
                "Lines with increasing loss ratio",
                row["loss_ratio_change"],
                row["year"],
                "Market",
                row["line_of_business_standard"],
                "Loss ratio increased versus prior available year.",
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
                "Highest loss ratio companies",
                "Companies losing market share",
                "Lines with increasing loss ratio",
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
