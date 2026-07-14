import streamlit as st

from src import data, query
from src.ui.components import render_layer_header, render_rows


def render_bronze() -> None:
    label_en, label_zh, rows = query.LAYERS["bronze"]
    render_layer_header(label_en, label_zh)

    row_counts = data.load_query(query.BronzeRowCounts())
    pipe_status = data.load_query(query.BronzePipeStatus())
    copy_history = data.load_query(query.BronzeCopyHistory())

    pending = int(pipe_status["PENDING_FILE_COUNT"].sum()) if not pipe_status.empty else 0
    running = int((pipe_status["EXECUTION_STATE"] == "RUNNING").sum()) if not pipe_status.empty else 0
    errors = int(copy_history["ERROR_COUNT"].sum()) if "ERROR_COUNT" in copy_history.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bronze tables", len(row_counts))
    c2.metric("Pipes running", f"{running}/{len(pipe_status)}")
    c3.metric("Pending files", pending)
    c4.metric("Copy errors (14d)", errors)

    render_rows(rows)
