"""
The purpose of this module is to provide functions to load various data sets
"""

import pandas as pd

from hotels import DATA_DIR

COUNTRY_CODE_PATH = DATA_DIR / "country_code.csv"
hotel_raw_data_path = DATA_DIR / "raw" / "hotels.parquet"
bookings_data_path = DATA_DIR / "cleaned" / "bookings.parquet"
action_data_path = DATA_DIR / "aggregated" / "action.parquet"


def load_raw_hotel_data() -> pd.DataFrame:
    return pd.read_parquet(hotel_raw_data_path)


def load_country_code_mapping() -> dict[str, str]:
    """Mapping table between country code (such as JPN) and country name (Japan)"""
    df = pd.read_csv(COUNTRY_CODE_PATH)
    return df.set_index("code")["country"].to_dict()


def load_booking_data() -> pd.DataFrame:
    return pd.read_parquet(bookings_data_path)


def load_action_data() -> pd.DataFrame:
    return pd.read_parquet(action_data_path)
