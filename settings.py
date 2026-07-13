import os

import streamlit as st
from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    is_local: bool
    snowflake_connection_ttl: int | None = None


# --------------- SNOWFLAKE DETECTION ---------------
@st.cache_resource
def get_settings() -> Settings:
    # SiS session token file only exists inside Snowflake -> Use Snowflake live data.
    is_local = not os.path.isfile("/snowflake/session/token")
    return Settings(is_local=is_local)
