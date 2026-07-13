import streamlit as st

from settings import get_settings
from src import theme, ui


st.set_page_config(
    page_title="LEAGUE_SNOWFLAKE Pipeline Monitor",
    layout="wide",
)

settings = get_settings()
theme.inject(st)
ui.render_header(settings)

with st.sidebar:
    st.markdown("### Navigation · 导航")
    section = st.radio(
        "Jump to layer",
        options=["All layers", "Seed", "Bronze", "Silver", "Gold"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(
        "This dashboard summarizes models/*/monitor.ipynb. "
        "For raw data previews or ad-hoc inspection, open the notebook "
        "for the relevant layer directly in Snowsight."
    )

if section in ("All layers", "Seed"):
    ui.render_seed(settings)
if section in ("All layers", "Bronze"):
    ui.render_bronze(settings)
if section in ("All layers", "Silver"):
    ui.render_silver(settings)
if section in ("All layers", "Gold"):
    ui.render_gold(settings)
