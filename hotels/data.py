from abc import ABC, abstractmethod
from typing import Dict
import datetime as dt

import pandas as pd

from hotels import DATA_PATH, DATA_URL, COUNTRY_CODE_PATH


def download_data():
    df = pd.read_csv(DATA_URL)
    df.to_parquet(DATA_PATH)
    print(f"DOWNLOADED: {DATA_PATH}")


class DataLoader(ABC):
    @abstractmethod
    def load_raw_data(self) -> pd.DataFrame:
        raise NotImplemented

    @abstractmethod
    def get_min_date(self) -> dt.date:
        raise NotImplemented

    @abstractmethod
    def get_max_date(self) -> dt.date:
        raise NotImplemented


def load_country_code_mapping() -> Dict[str, str]:
    df = pd.read_csv(COUNTRY_CODE_PATH)
    return df.set_index("code")["country"].to_dict()
