import os

import pandas as pd


# --------------- FILE CONSTANTS ---------------
SAMPLE_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets",
    "sample_data"
)


# --------------- MOCK SAMPLE DATA ---------------
def read(name: str) -> pd.DataFrame:
    path = os.path.join(SAMPLE_DATA_DIR, f"{name}.csv")
    return pd.read_csv(path)
