import pandas as pd
from tqdm.auto import tqdm

from hotels.load_data import load_booking_data, action_data_path

tqdm.pandas()


def _reservation2actions(row: pd.Series) -> pd.DataFrame:
    stays = pd.date_range(row["arrival_date"], row["actual_departure_date"])
    actions = ["arrival"] + ["stay"] * (len(stays) - 2) + ["departure"]
    return pd.DataFrame({"reservation_id": row["reservation_id"], "date": stays, "action": actions})


def build_action_data():
    """
    Processing the cleaned data we create a table showing which guests arrive/stay/leave.
    """
    df_booking = load_booking_data()
    df_actions = pd.concat(
        df_booking.query("is_canceled == 0 and n_stay_actual > 0")
        .progress_apply(_reservation2actions, axis=1)
        .to_list(),
        axis=0,
    )
    df_actions.to_parquet(action_data_path)
