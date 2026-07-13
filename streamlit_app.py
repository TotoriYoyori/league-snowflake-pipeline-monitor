import streamlit as st

from src import theme, ui
from src import query as q


st.set_page_config(
    page_title="LEAGUE_SNOWFLAKE Pipeline Monitor",
    layout="wide",
)

theme.inject(st)
ui.render_header()

ALL_LAYERS_LABEL = "All layers · 全部层"

seed_en, seed_zh, _ = q.LAYERS["seed"]
bronze_en, bronze_zh, _ = q.LAYERS["bronze"]
silver_en, silver_zh, _ = q.LAYERS["silver"]
gold_en, gold_zh, _ = q.LAYERS["gold"]

seed_label = f"{seed_en} · {seed_zh}"
bronze_label = f"{bronze_en} · {bronze_zh}"
silver_label = f"{silver_en} · {silver_zh}"
gold_label = f"{gold_en} · {gold_zh}"

with st.sidebar:
    st.markdown("### Navigation · 导航")
    section = st.radio(
        "Jump to layer",
        options=[ALL_LAYERS_LABEL, seed_label, bronze_label, silver_label, gold_label],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(
        "This dashboard summarizes models/*/monitor.ipynb. "
        "For raw data previews or ad-hoc inspection, open the notebook "
        "for the relevant layer directly in Snowsight."
    )
    st.caption(
        "本仪表盘汇总自 models/*/monitor.ipynb。"
        "如果需要预览原始数据或进行临时排查，请直接在 Snowsight 中打开对应层级的 Notebook。"
    )

if section in (ALL_LAYERS_LABEL, seed_label):
    ui.render_seed()
if section in (ALL_LAYERS_LABEL, bronze_label):
    ui.render_bronze()
if section in (ALL_LAYERS_LABEL, silver_label):
    ui.render_silver()
if section in (ALL_LAYERS_LABEL, gold_label):
    ui.render_gold()
