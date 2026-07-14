import streamlit as st

from src import data, query
from src.ui.components import render_check, render_layer_header, render_rows


def render_silver() -> None:
    label_en, label_zh, rows = query.LAYERS["silver"]
    render_layer_header(label_en, label_zh)

    task_summary = data.load_query(query.SilverTaskSummary())
    vs_gold = data.load_query(query.SilverVsGoldCounts())
    row_counts = data.load_query(query.SilverRowCounts())

    failed = int((task_summary["STATE"] != "SUCCEEDED").sum()) if "STATE" in task_summary.columns else 0
    diff_total = int(vs_gold["DIFF"].abs().sum()) if "DIFF" in vs_gold.columns else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Task states w/ failures (24h)", failed)
    c2.metric("Silver tables", len(row_counts))
    c3.metric("Silver↔Gold row diff", diff_total)

    # Special-shaped
    render_check(query.SilverObjectInventory(), data.load_silver_object_inventory())
    render_rows(rows)
