import datetime as dt

import pandas as pd

from hotels import DATA_PATH
from hotels.data import DataLoader


class DataLoaderLocal(DataLoader):
    def load_raw_data(self) -> pd.DataFrame:
        df = pd.read_parquet(DATA_PATH)
        return df

    def get_min_date(self) -> dt.date:
        return dt.date(2015, 7, 1)

    def get_max_date(self) -> dt.date:
        return dt.date(2017, 8, 31)
