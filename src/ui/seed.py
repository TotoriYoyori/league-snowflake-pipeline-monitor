import streamlit as st

from src import data, query
from src.ui.components import count_status, render_layer_header, render_rows


def render_seed() -> None:
    label_en, label_zh, rows = query.LAYERS["seed"]
    render_layer_header(label_en, label_zh)

    row_validation = data.load_query(query.SeedRowCountValidation())
    load_state = data.load_query(query.SeedLoadState())

    ok, total = count_status(row_validation, "STATUS", ("PASS",))
    c1, c2, c3 = st.columns(3)
    c1.metric("Seed datasets validated", f"{ok}/{total}")
    if not load_state.empty and {"DAYS_INGESTED", "DAYS_REMAINING"}.issubset(load_state.columns):
        c2.metric("Days ingested", int(load_state.iloc[0]["DAYS_INGESTED"]))
        c3.metric("Days remaining", int(load_state.iloc[0]["DAYS_REMAINING"]))

    render_rows(rows)
