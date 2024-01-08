import datetime as dt

import pandas as pd
import pandera as pa

from hotels.load_data import load_action_data


class ActionDataSchema(pa.DataFrameModel):
    reservation_id: str = pa.Field(nullable=False)
    date: dt.datetime = pa.Field(nullable=False)
    action: str = pa.Field(nullable=False, isin=["arrival", "stay", "departure"])

    @pa.dataframe_check
    def check_number_of_arrivals_1(cls, df: pd.DataFrame) -> bool:
        """Use the pseudo Hotel PMS Dashboard to find the expected number"""
        selected_date = dt.datetime(2015, 12, 30)
        n_arrivals = (
            df.query("date == @selected_date").query("action == 'arrival'")["reservation_id"].str.startswith("C").sum()
        )
        return n_arrivals == 66 - 4  # expected arrivals - no-shows

    @pa.dataframe_check
    def check_number_of_arrivals_2(cls, df: pd.DataFrame) -> bool:
        """Use the pseudo Hotel PMS Dashboard to find the expected number"""
        selected_date = dt.datetime(2016, 1, 8)
        n_arrivals = (
            df.query("date == @selected_date").query("action == 'arrival'")["reservation_id"].str.startswith("C").sum()
        )
        return n_arrivals == 29 - 1  # there is one reservation without staying at night.

    @pa.dataframe_check
    def check_number_of_staying_guests(cls, df: pd.DataFrame) -> bool:
        """Actually we see the number of reservations instead of the guests"""
        selected_date = dt.datetime(2016, 7, 19)
        n_staying_guests = (
            df.query("date == @selected_date").query("action == 'stay'")["reservation_id"].str.startswith("R").sum()
        )
        ## NB: The guests with action = 'arrival' will stay at night, but they are not included in n_staying_guests
        return n_staying_guests == 143


def test_action_data():
    df = load_action_data()

    try:
        ActionDataSchema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        with pd.option_context("display.max_columns", None, "display.max_colwidth", None):
            print(e.failure_cases)
        raise e
