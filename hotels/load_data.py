"""
The purpose of this module is to provide functions to load various data sets
"""

import pandas as pd
import dvc.api as dvc

from hotels import DATA_DIR

hotel_raw_data_path = DATA_DIR / "raw" / "hotels.parquet"
bookings_data_path = DATA_DIR / "cleaned" / "bookings.parquet"
actions_data_path = DATA_DIR / "aggregated" / "actions.parquet"

fs = dvc.DVCFileSystem(uel="https://github.com/stdiff/hotels", rev="main")


def load_raw_hotel_data() -> pd.DataFrame:
    with fs.open("/data/raw/hotels.parquet") as fo:
        return pd.read_parquet(fo)


def load_country_code_mapping() -> dict[str, str]:
    """Mapping table between country code (such as JPN) and country name (Japan)"""
    with fs.open("/data/country_code.csv") as fo:
        df = pd.read_csv(fo)
    return df.set_index("code")["country"].to_dict()


def load_booking_data() -> pd.DataFrame:
    with fs.open("/data/cleaned/bookings.parquet") as fo:
        return pd.read_parquet(fo)


def load_action_data() -> pd.DataFrame:
    with fs.open("/data/aggregated/actions.parquet") as fo:
        return pd.read_parquet(fo)
