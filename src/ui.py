import textwrap

import pandas as pd
import streamlit as st

from src import data as d
from src import query as q

# --------------- CONSTANTS ---------------
PILL_OK = "pm-pill-ok"
PILL_WARN = "pm-pill-warn"
PILL_FAIL = "pm-pill-fail"
PILL_NEUTRAL = "pm-pill-neutral"

APP_TITLE = "Pipeline Monitor"
APP_SUBTITLE_EN = "League of Legends Snowflake Pipeline Monitoring Dashboard"
APP_SUBTITLE_ZH = "英雄联盟数据管道 — 健康与运行监控"

_PILL_LEVELS = {"ok": PILL_OK, "warn": PILL_WARN, "fail": PILL_FAIL}


def _pill(text: str, level: str = PILL_NEUTRAL) -> str:
    return f'<span class="pm-pill {level}">{text}</span>'


def _pill_level(level: str) -> str:
    return _PILL_LEVELS.get(level, PILL_NEUTRAL)


# --------------- RENDERING ---------------
def render_header() -> None:
    mode_label = "Local / Mock" if d.IS_LOCAL else "Snowflake (live)"
    mode_level = PILL_NEUTRAL if d.IS_LOCAL else PILL_OK
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
    check: q.MonitorQuery,
    df: pd.DataFrame,
    height: int | None = None
) -> None:
    """Render one check's card, sourcing its title/description/status from
    the check itself. Shows a failed-load state if `df` came from a failed
    fetch (see data.load_error)."""
    error = d.load_error(df)
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


def render_rows(rows: list[list[q.MonitorQuery]]) -> None:
    for row in rows:
        if len(row) == 1:
            check = row[0]
            render_check(check, d.load_query(check))
        else:
            height = 220 if len(row) >= 3 else None
            cols = st.columns(len(row))
            for col, check in zip(cols, row):
                with col:
                    render_check(check, d.load_query(check), height=height)


def _count_status(
    df: pd.DataFrame,
    col: str,
    ok_values: tuple[str, ...]
) -> tuple[int, int]:
    if df.empty or col not in df.columns:
        return 0, 0

    total = len(df)
    ok = df[col].isin(ok_values).sum()
    return int(ok), total


# ===========================================================================
# SEED
# ===========================================================================
def render_seed() -> None:
    label_en, label_zh, rows = q.LAYERS["seed"]
    render_layer_header(label_en, label_zh)

    row_validation = d.load_query(q.SeedRowCountValidation())
    load_state = d.load_query(q.SeedLoadState())

    ok, total = _count_status(row_validation, "STATUS", ("PASS",))
    c1, c2, c3 = st.columns(3)
    c1.metric("Seed datasets validated", f"{ok}/{total}")
    if not load_state.empty and {"DAYS_INGESTED", "DAYS_REMAINING"}.issubset(load_state.columns):
        c2.metric("Days ingested", int(load_state.iloc[0]["DAYS_INGESTED"]))
        c3.metric("Days remaining", int(load_state.iloc[0]["DAYS_REMAINING"]))

    render_rows(rows)


# ===========================================================================
# BRONZE
# ===========================================================================
def render_bronze() -> None:
    label_en, label_zh, rows = q.LAYERS["bronze"]
    render_layer_header(label_en, label_zh)

    row_counts = d.load_query(q.BronzeRowCounts())
    pipe_status = d.load_query(q.BronzePipeStatus())
    copy_history = d.load_query(q.BronzeCopyHistory())

    pending = int(pipe_status["PENDING_FILE_COUNT"].sum()) if not pipe_status.empty else 0
    running = int((pipe_status["EXECUTION_STATE"] == "RUNNING").sum()) if not pipe_status.empty else 0
    errors = int(copy_history["ERROR_COUNT"].sum()) if "ERROR_COUNT" in copy_history.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bronze tables", len(row_counts))
    c2.metric("Pipes running", f"{running}/{len(pipe_status)}")
    c3.metric("Pending files", pending)
    c4.metric("Copy errors (14d)", errors)

    render_rows(rows)


# ===========================================================================
# SILVER
# ===========================================================================
def render_silver() -> None:
    label_en, label_zh, rows = q.LAYERS["silver"]
    render_layer_header(label_en, label_zh)

    task_summary = d.load_query(q.SilverTaskSummary())
    vs_gold = d.load_query(q.SilverVsGoldCounts())
    row_counts = d.load_query(q.SilverRowCounts())

    failed = int((task_summary["STATE"] != "SUCCEEDED").sum()) if "STATE" in task_summary.columns else 0
    diff_total = int(vs_gold["DIFF"].abs().sum()) if "DIFF" in vs_gold.columns else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Task states w/ failures (24h)", failed)
    c2.metric("Silver tables", len(row_counts))
    c3.metric("Silver↔Gold row diff", diff_total)

    # Special-shaped
    render_check(q.SilverObjectInventory(), d.load_silver_object_inventory())
    render_rows(rows)


# ===========================================================================
# GOLD
# ===========================================================================
def render_gold() -> None:
    label_en, label_zh, _rows = q.LAYERS["gold"]
    render_layer_header(label_en, label_zh)

    inventory = d.load_query(q.GoldObjectInventory())
    freshness = d.load_gold_dt_freshness()
    refresh_history = d.load_query(q.GoldRefreshHistory())
    grain = d.load_query(q.GoldGrainValidation())

    behind = int((~freshness["FRESHNESS_STATUS"].astype(str).str.contains("ON TRACK")).sum()) \
        if "FRESHNESS_STATUS" in freshness.columns \
        else 0
    refresh_failures = int((refresh_history["REFRESH_STATE"] != "SUCCEEDED").sum()) \
        if "REFRESH_STATE" in refresh_history.columns \
        else 0
    grain_fail = int((grain["STATUS"] != "PASS").sum()) \
        if "STATUS" in grain.columns \
        else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Dynamic tables", len(inventory))
    c2.metric("Not on track", behind)
    c3.metric("Grain checks failing", grain_fail)

    # Special-shaped
    render_check(q.GoldObjectInventory(), inventory)
    render_check(q.GoldDtFreshness(), freshness)
    render_check(q.GoldRefreshHistory(), refresh_history)
    render_check(q.GoldGrainValidation(), grain)
