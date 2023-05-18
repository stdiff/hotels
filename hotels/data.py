from typing import Dict
import datetime as dt

import pandas as pd

from hotels import DATA_PATH, DATA_URL, COUNTRY_CODE_PATH


def download_data():
    df = pd.read_csv(DATA_URL)
    df.to_parquet(DATA_PATH)
    print(f"DOWNLOADED: {DATA_PATH}")


def load_raw_data_from_local() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    return df


def get_min_date() -> dt.date:
    return dt.date(2015, 7, 1)


def get_max_date() -> dt.date:
    return dt.date(2017, 8, 31)


def load_country_code_mapping() -> Dict[str, str]:
    df = pd.read_csv(COUNTRY_CODE_PATH)
    return df.set_index("code")["country"].to_dict()
