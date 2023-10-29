from typing import Dict
import datetime as dt

import pandas as pd

from hotels import DATA_PATH, DATA_URL, COUNTRY_CODE_PATH

min_date = dt.date(2015, 7, 1)
max_date = dt.date(2017, 8, 31)


def download_raw_data():
    df = pd.read_csv(DATA_URL)
    df.to_parquet(DATA_PATH)
    print(f"DOWNLOADED: {DATA_PATH}")


def load_raw_data() -> pd.DataFrame:
    """Original data without any preprocessing"""
    if not DATA_PATH.exists():
        download_raw_data()

    return pd.read_parquet(DATA_PATH)


def load_country_code_mapping() -> Dict[str, str]:
    """Mapping table between country code (such as JPN) and country name (Japan)"""
    df = pd.read_csv(COUNTRY_CODE_PATH)
    return df.set_index("code")["country"].to_dict()
