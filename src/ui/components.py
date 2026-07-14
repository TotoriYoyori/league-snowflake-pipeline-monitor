import textwrap

import pandas as pd
import streamlit as st

from src import data, query

# --------------- APP LABELING ---------------
APP_TITLE = "Pipeline Monitor"
APP_SUBTITLE_EN = "League of Legends Snowflake Pipeline Monitoring Dashboard"
APP_SUBTITLE_ZH = "英雄联盟数据管道 — 健康与运行监控"

# --------------- STATUS PILLS (CSS classes defined in theme.py) ---------------
PILL_OK = "pm-pill-ok"
PILL_WARN = "pm-pill-warn"
PILL_FAIL = "pm-pill-fail"
PILL_NEUTRAL = "pm-pill-neutral"

_PILL_LEVELS = {"ok": PILL_OK, "warn": PILL_WARN, "fail": PILL_FAIL}


def _pill(text: str, level: str = PILL_NEUTRAL) -> str:
    return f'<span class="pm-pill {level}">{text}</span>'


def _pill_level(level: str) -> str:
    return _PILL_LEVELS.get(level, PILL_NEUTRAL)


# --------------- RENDERING ---------------
def render_header() -> None:
    mode_label = "Local / Mock" if data.IS_LOCAL else "Snowflake (live)"
    mode_level = PILL_NEUTRAL if data.IS_LOCAL else PILL_OK
    st.markdown(
        textwrap.dedent(f"""
        <div class="pm-header">
            <div class="pm-title">{APP_TITLE} {_pill(mode_label, mode_level)}</div>
            <div class="pm-subtitle-en">{APP_SUBTITLE_EN}</div>
            <div class="pm-subtitle-zh">{APP_SUBTITLE_ZH}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def render_layer_header(label_en: str, label_zh: str) -> None:
    st.markdown(
        textwrap.dedent(f"""
        <div class="pm-layer-header">
            <span class="pm-layer-en">{label_en}</span>
            <span class="pm-layer-zh">{label_zh}</span>
        </div>
        """),
        unsafe_allow_html=True,
    )


def render_card(
    name_en: str,
    name_zh: str,
    desc_en: str,
    df: pd.DataFrame,
    status_text: str | None = None,
    status_level: str = PILL_NEUTRAL,
    height: int | None = None,
) -> None:
    pill_html = _pill(status_text, status_level) if status_text else ""
    with st.container(border=True):
        st.markdown(
            textwrap.dedent(f"""
            <div class="pm-card-title">
                <div>
                    <div class="pm-card-name">{name_en} · <span style="font-weight:400;color:var(--ink-soft);">{name_zh}</span></div>
                    <div class="pm-card-desc">{desc_en}</div>
                </div>
                {pill_html}
            </div>
            """),
            unsafe_allow_html=True,
        )
        st.dataframe(df, height=height or "content", hide_index=True)


def render_check(
    check: query.MonitorQuery,
    df: pd.DataFrame,
    height: int | None = None
) -> None:
    """Render one check's card, showing a failed-load state if `df` came from a failed fetch."""
    error = data.load_error(df)
    if error is not None:
        render_card(
            check.title_en, check.title_zh, check.desc_en, df,
            status_text="failed to load",
            status_level=PILL_FAIL,
            height=height,
        )
        st.caption(f"⚠️ {error}")
        return

    status = check.status(df)
    render_card(
        check.title_en, check.title_zh, check.desc_en, df,
        status_text=status[0] if status else None,
        status_level=_pill_level(status[1]) if status else PILL_NEUTRAL,
        height=height,
    )


def render_rows(rows: list[list[query.MonitorQuery]]) -> None:
    for row in rows:
        if len(row) == 1:
            check = row[0]
            render_check(check, data.load_query(check))
        else:
            height = 220 if len(row) >= 3 else None
            cols = st.columns(len(row))
            for col, check in zip(cols, row):
                with col:
                    render_check(check, data.load_query(check), height=height)


def count_status(
    df: pd.DataFrame,
    col: str,
    ok_values: tuple[str, ...]
) -> tuple[int, int]:
    if df.empty or col not in df.columns:
        return 0, 0

    total = len(df)
    ok = df[col].isin(ok_values).sum()
    return int(ok), total
