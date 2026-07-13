import os

import pandas as pd
import streamlit as st

from src import query as q


# --------------- CONSTANTS ---------------
SAMPLE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "assets", "sample_data"
)

# SiS session token file only exists inside Snowflake -> use Snowflake live data.
IS_LOCAL: bool = not os.path.isfile("/snowflake/session/token")


def read_mock(name: str) -> pd.DataFrame:
    path = os.path.join(SAMPLE_DATA_DIR, f"{name}.csv")
    return pd.read_csv(path)


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
    """Return the Snowpark session in SiS, or None when running locally."""
    if IS_LOCAL:
        return None

    conn = st.connection("snowflake", ttl=None)
    return conn.session()


def _run(session, sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()


# --------------- RUN QUERY AGAINST SNOWFLAKE (LIVE) OR READ FROM SAMPLE DATA ---------------
@st.cache_data(ttl=60, show_spinner="Loading…")
def _load(_query: q.MonitorQuery, cache_key: str) -> pd.DataFrame:
    try:
        if IS_LOCAL:
            return read_mock(_query.mock_file_name)

        return _run(get_session(), _query.build())
    except Exception as e:
        return _failed(str(e))


def load_query(query: q.MonitorQuery) -> pd.DataFrame:
    return _load(query, query.build())


# --------------- SPECIAL LOADERS (multi-query / session-order dependent) ---------------
def load_silver_object_inventory() -> pd.DataFrame:
    @st.cache_data(
        ttl=60,
        show_spinner="Loading silver object inventory…"
    )
    def _load():
        try:
            if IS_LOCAL:
                return read_mock("silver_object_inventory")

            session = get_session()
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
        except Exception as e:
            return _failed(str(e))

    return _load()


def load_gold_dt_freshness() -> pd.DataFrame:
    query = q.GoldDtFreshness()

    @st.cache_data(
        ttl=60,
        show_spinner="Checking dynamic table freshness…"
    )
    def _load():
        try:
            if IS_LOCAL:
                return read_mock(query.mock_file_name)

            session = get_session()
            session.sql(q.GoldObjectInventory().build()).collect()
            return _run(session, query.build())
        except Exception as e:
            return _failed(str(e))

    return _load()
