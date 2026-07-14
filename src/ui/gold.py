import streamlit as st

from src import data, query
from src.ui.components import render_check, render_layer_header


def render_gold() -> None:
    label_en, label_zh, _rows = query.LAYERS["gold"]
    render_layer_header(label_en, label_zh)

    inventory = data.load_query(query.GoldObjectInventory())
    freshness = data.load_gold_dt_freshness()
    refresh_history = data.load_query(query.GoldRefreshHistory())
    grain = data.load_query(query.GoldGrainValidation())

    behind = int((~freshness["FRESHNESS_STATUS"].astype(str).str.contains("ON TRACK")).sum()) \
        if "FRESHNESS_STATUS" in freshness.columns \
        else 0
    refresh_failures = int((refresh_history["REFRESH_STATE"] != "SUCCEEDED").sum()) \
        if "REFRESH_STATE" in refresh_history.columns \
        else 0
    grain_fail = int((grain["STATUS"] != "PASS").sum()) \
        if "STATUS" in grain.columns \
        else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Dynamic tables", len(inventory))
    c2.metric("Not on track", behind)
    c3.metric("Grain checks failing", grain_fail)
    c4.metric("Refresh failures (recent)", refresh_failures)

    render_check(query.GoldObjectInventory(), inventory)
    render_check(query.GoldDtFreshness(), freshness)
    render_check(query.GoldRefreshHistory(), refresh_history)
    render_check(query.GoldGrainValidation(), grain)
