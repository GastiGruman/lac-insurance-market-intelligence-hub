from __future__ import annotations

import html
import plotly.graph_objects as go
import streamlit as st


NAVY = "#071D3A"
BLUE = "#005EB8"
LIGHT_BLUE = "#EAF3FF"
GREY_BG = "#F3F6FA"
BORDER = "#D9E2EC"
TEXT = "#16202A"
MUTED = "#66788A"


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --navy: {NAVY};
            --blue: {BLUE};
            --light-blue: {LIGHT_BLUE};
            --grey-bg: {GREY_BG};
            --border: {BORDER};
            --text: {TEXT};
            --muted: {MUTED};
        }}

        .block-container {{
            padding-top: 1.3rem;
            padding-bottom: 2.2rem;
            max-width: 1380px;
        }}

        section[data-testid="stSidebar"] {{
            background: #F8FAFC;
            border-right: 1px solid var(--border);
        }}

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: var(--navy);
        }}

        div[data-testid="stMetric"] {{
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 6px rgba(15, 23, 42, 0.06);
        }}

        div[data-testid="stMetricLabel"] p {{
            color: var(--muted);
            font-size: 0.78rem;
            letter-spacing: 0;
        }}

        div[data-testid="stMetricValue"] {{
            color: var(--navy);
            font-weight: 700;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 1px solid var(--border);
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 44px;
            padding: 0 12px;
            border-radius: 6px 6px 0 0;
            color: var(--muted);
            font-weight: 600;
        }}

        .stTabs [aria-selected="true"] {{
            background: var(--light-blue);
            color: var(--navy);
        }}

        div.stButton > button,
        div.stDownloadButton > button {{
            border-radius: 6px;
            border: 1px solid var(--blue);
            color: var(--blue);
            background: #FFFFFF;
            font-weight: 600;
        }}

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {{
            border-color: var(--navy);
            color: var(--navy);
            background: var(--light-blue);
        }}

        .app-header {{
            background: linear-gradient(135deg, #071D3A 0%, #0B2E59 100%);
            border-radius: 10px;
            padding: 22px 26px;
            color: #FFFFFF;
            margin-bottom: 18px;
            box-shadow: 0 8px 24px rgba(7, 29, 58, 0.18);
        }}

        .app-kicker {{
            color: #A9C7EA;
            font-size: 0.78rem;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.08em;
            margin-bottom: 6px;
        }}

        .app-title {{
            font-size: 1.85rem;
            line-height: 1.15;
            font-weight: 750;
            margin: 0;
        }}

        .app-subtitle {{
            color: #D8E7F7;
            font-size: 0.96rem;
            max-width: 860px;
            margin-top: 8px;
        }}

        .info-card,
        .metric-card {{
            background: #FFFFFF;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 1px 8px rgba(15, 23, 42, 0.06);
        }}

        .metric-card {{
            margin-bottom: 10px;
        }}

        .metric-card-label {{
            color: var(--muted);
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 8px;
        }}

        .metric-card-value {{
            color: var(--navy);
            font-size: 1.18rem;
            font-weight: 760;
            line-height: 1.18;
            white-space: normal;
            overflow-wrap: anywhere;
        }}

        .metric-card-help {{
            color: var(--muted);
            font-size: 0.78rem;
            margin-top: 8px;
        }}

        .section-heading {{
            border-left: 4px solid var(--blue);
            padding-left: 12px;
            margin: 22px 0 12px 0;
        }}

        .section-heading h3 {{
            color: var(--navy);
            font-size: 1.1rem;
            margin: 0;
        }}

        .section-heading p {{
            color: var(--muted);
            font-size: 0.86rem;
            margin: 3px 0 0 0;
        }}

        .status-pill {{
            display: inline-block;
            padding: 4px 9px;
            border-radius: 999px;
            background: var(--light-blue);
            color: var(--navy);
            border: 1px solid #B7D8FF;
            font-size: 0.76rem;
            font-weight: 700;
        }}

        .status-strip {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: -4px 0 16px 0;
        }}

        .empty-state {{
            background: #FFFFFF;
            border: 1px dashed var(--border);
            border-radius: 8px;
            padding: 18px;
            color: var(--text);
        }}

        .empty-state-title {{
            color: var(--navy);
            font-weight: 760;
            margin-bottom: 6px;
        }}

        .empty-state-body {{
            color: var(--muted);
            font-size: 0.9rem;
            margin: 0;
        }}

        .sidebar-label {{
            color: var(--navy);
            font-weight: 760;
            font-size: 0.82rem;
            margin: 14px 0 6px 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def configure_plotly_theme() -> None:
    import plotly.express as px
    import plotly.io as pio

    template = go.layout.Template()
    template.layout = go.Layout(
        font=dict(family="Arial, sans-serif", color=TEXT, size=12),
        title=dict(font=dict(color=NAVY, size=18), x=0.02, xanchor="left"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=[BLUE, "#00A3E0", "#4B5563", "#7EA6D8", "#93C5FD", "#64748B"],
        xaxis=dict(showgrid=False, zeroline=False, linecolor=BORDER),
        yaxis=dict(gridcolor="#E8EEF5", zeroline=False, linecolor=BORDER),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=24, t=64, b=48),
    )
    pio.templates["market_intel"] = template
    pio.templates.default = "market_intel"
    px.defaults.template = "market_intel"
    px.defaults.color_discrete_sequence = [BLUE, "#00A3E0", "#4B5563", "#7EA6D8", "#93C5FD"]


def render_top_header(title: str, subtitle: str, kicker: str = "Internal Market Intelligence") -> None:
    st.markdown(
        f"""
        <div class="app-header">
          <div class="app-kicker">{html.escape(kicker)}</div>
          <h1 class="app-title">{html.escape(title)}</h1>
          <div class="app-subtitle">{html.escape(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, help_text: str | None = None) -> None:
    help_html = f'<div class="metric-card-help">{html.escape(help_text)}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-card-label">{html.escape(label)}</div>
          <div class="metric-card-value">{html.escape(str(value))}</div>
          {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div class="section-heading">
          <h3>{html.escape(title)}</h3>
          {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_pill(label: str) -> None:
    st.markdown(f'<span class="status-pill">{html.escape(label)}</span>', unsafe_allow_html=True)


def render_status_strip(items: list[str]) -> None:
    pills = "".join(f'<span class="status-pill">{html.escape(item)}</span>' for item in items)
    st.markdown(f'<div class="status-strip">{pills}</div>', unsafe_allow_html=True)


def render_empty_state(message: str, next_step: str | None = None) -> None:
    next_step_html = f" {html.escape(next_step)}" if next_step else ""
    st.markdown(
        f"""
        <div class="empty-state">
          <div class="empty-state-title">{html.escape(message)}</div>
          <p class="empty-state-body">{next_step_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_label(label: str) -> None:
    st.sidebar.markdown(f'<div class="sidebar-label">{html.escape(label)}</div>', unsafe_allow_html=True)
