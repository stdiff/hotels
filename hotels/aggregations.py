from enum import Enum
import pandas as pd

from hotels.models import Hotel


def compute_occupancy_rate(df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame, hotel: Hotel) -> pd.DataFrame:
    """
    PK = (hotel, date)

    :return: DataFrame[hotel, date, n_occupied_rooms, n_available_rooms, occupancy_rate]
    """
    df_occupancy_rate = (
        df_room_usage.query("hotel == @hotel")
        .groupby(["hotel", "date"], as_index=False)["n_occupied_rooms"]
        .sum()
        .merge(df_room_count.groupby("hotel")["n_rooms"].sum().rename("n_available_rooms").reset_index())
        .assign(occupancy_rate=lambda x: x["n_occupied_rooms"] / x["n_available_rooms"])
    )
    return df_occupancy_rate
