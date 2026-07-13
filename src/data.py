import os

import pandas as pd
import streamlit as st

from src import query as q
from settings import get_settings, Settings


# --------------- CONSTANTS ---------------
SAMPLE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "sample_data"
)


def read_mock(name: str) -> pd.DataFrame:
    path = os.path.join(SAMPLE_DATA_DIR, f"{name}.csv")
    return pd.read_csv(path)


# --------------- SETTINGS AND SESSIONS ---------------
settings = get_settings()


@st.cache_resource
def get_session(_settings: Settings):
    """Return the Snowpark session in SiS, or None when running locally."""
    if _settings.is_local:
        return None

    conn = st.connection(
        "snowflake",
        ttl=_settings.snowflake_connection_ttl
    )
    return conn.session()


def _run(session, sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# --------------- RUN QUERY AGAINST SNOWFLAKE (LIVE) OR READ FROM SAMPLE DATA ---------------
def load_query(query: q.MonitorQuery) -> pd.DataFrame:
    """Generic loader for any MonitorQuery with a `.build()` and
    `mock_file_name`. Covers every check except the two special-shaped
    loaders below."""

    @st.cache_data(
        ttl=query.ttl,
        show_spinner=f"Loading {query.mock_file_name.replace('_', ' ')}…"
    )
    def _load():
        if settings.is_local:
            return read_mock(query.mock_file_name)

        return _run(
            get_session(settings),
            query.build()
        )

    return _load()


# --------------- SPECIAL LOADERS (multi-query / session-order dependent) ---------------
def load_silver_object_inventory() -> pd.DataFrame:
    @st.cache_data(
        ttl=60,
        show_spinner="Loading silver object inventory…"
    )
    def _load():
        if settings.is_local:
            return read_mock("silver_object_inventory")

        session = get_session(settings)
        sq = q.SilverObjectInventory()
        tables = _run(session, sq.build_tables())
        views = _run(session, sq.build_views())
        tasks = _run(session, sq.build_tasks())
        tables["OBJECT_TYPE"], tasks["OBJECT_TYPE"], views["OBJECT_TYPE"] = (
            "TABLE", "TASK", "VIEW"
        )
        cols = ["OBJECT_TYPE", "name"]
        combined = pd.concat(
            [tables[cols], views[cols], tasks[cols]], ignore_index=True
        ).rename(columns={"name": "OBJECT_NAME"})
        return combined

    return _load()


def load_gold_dt_freshness() -> pd.DataFrame:
    query = q.GoldDtFreshness()

    @st.cache_data(
        ttl=query.ttl,
        show_spinner="Checking dynamic table freshness…"
    )
    def _load():
        if settings.is_local:
            return read_mock(query.mock_file_name)
        # Must run SHOW DYNAMIC TABLES immediately before the RESULT_SCAN
        # query, in the same session, matching the notebook's pattern.
        session = get_session(settings)
        session.sql(q.GoldObjectInventory().build()).collect()
        return _run(
            session,
            query.build()
        )

    return _load()
