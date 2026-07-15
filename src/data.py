import os

import pandas as pd
import streamlit as st

from src import mock, query


# --------------- CONSTANTS ---------------
# SiS session token file only exists inside Snowflake -> use Snowflake live data.
IS_LOCAL: bool
try:
    conn = st.connection("snowflake")
    IS_LOCAL = False
except:
    IS_LOCAL = True

CACHE_TTL = 60


# --------------- FAILURE HANDLING ---------------
def _failed(message: str) -> pd.DataFrame:
    df = pd.DataFrame()
    df.attrs["error"] = message

    return df


def load_error(df: pd.DataFrame) -> str | None:
    """The error message if `df` came from a failed load, else None."""
    return df.attrs.get("error")


# --------------- SESSIONS ---------------
@st.cache_resource
def get_session():
    if IS_LOCAL:
        return None

    conn = st.connection("snowflake", ttl=None)
    session = conn.session()
    session.use_warehouse("COMPUTE_WH")

    return session


def _run(session, sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# --------------- RUN QUERY AGAINST SNOWFLAKE (LIVE) OR READ FROM SAMPLE DATA ---------------
@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading…")
def _load(_query: query.MonitorQuery, cache_key: str) -> pd.DataFrame:
    try:
        if IS_LOCAL:
            return mock.read(_query.mock_file_name)

        return _run(get_session(), _query.build())
    except Exception as e:
        return _failed(str(e))


def load_query(q: query.MonitorQuery) -> pd.DataFrame:
    return _load(q, q.build())


# --------------- SPECIAL LOADERS (multi-query / session-order dependent) ---------------
@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading silver object inventory…")
def load_silver_object_inventory() -> pd.DataFrame:
    try:
        if IS_LOCAL:
            return mock.read("silver_object_inventory")

        session = get_session()
        sq = query.SilverObjectInventory()
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
    except Exception as e:
        return _failed(str(e))


@st.cache_data(ttl=CACHE_TTL, show_spinner="Checking dynamic table freshness…")
def load_gold_dt_freshness() -> pd.DataFrame:
    dt_freshness_query = query.GoldDtFreshness()
    try:
        if IS_LOCAL:
            return mock.read(dt_freshness_query.mock_file_name)

        session = get_session()
        session.sql(query.GoldObjectInventory().build()).collect()
        return _run(session, dt_freshness_query.build())
    except Exception as e:
        return _failed(str(e))
