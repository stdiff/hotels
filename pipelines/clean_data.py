"""
The purpose of this module is to make the raw data analysis-ready
"""

from typing import Optional

import pandas as pd

from hotels.load_data import load_raw_hotel_data, load_country_code_mapping, bookings_data_path
from hotels.models import ReservationStatus


def convert_country_4_human(data: pd.DataFrame):
    """in-place operator"""
    code2country = load_country_code_mapping()
    data["country"] = data["country"].apply(lambda x: code2country.get(x, x))


def _rows_to_date(data: pd.DataFrame) -> pd.Series:
    s_date_str = (
        data["arrival_date_day_of_month"].apply(lambda x: f"{x:02d}")
        + "/"
        + data["arrival_date_month"]
        + "/"
        + data["arrival_date_year"].apply(str)
    )
    return pd.to_datetime(s_date_str, format="%d/%B/%Y")


class Preprocessor:
    """all methods are static methods which manipulate dataframes in place except apply_all()"""

    @staticmethod
    def convert_data_type(df: pd.DataFrame):
        df["reservation_status_date"] = pd.to_datetime(df["reservation_status_date"])

    @staticmethod
    def remove_invalid_records(df: pd.DataFrame):
        """
        - Add a column n_lodgers (number of people in the reservation)
        - Remove rows (reservations) with no lodgers (invalid reservations)
        """
        df["n_lodgers"] = df["adults"] + df["children"] + df["babies"]
        df.query("n_lodgers > 0", inplace=True)  ## invalid records

    @staticmethod
    def add_arrival_date(df: pd.DataFrame):
        """
        - Add a datetime column arrival_date by combining year, month, day_of_month columns.
        - Add the number of nights to stay.
        - Add the date for departure.
        - Add the total transaction

        The last two columns are just plan. A lodger might leave before his departure date.
        """
        df["arrival_date"] = _rows_to_date(df)
        df["n_nights"] = df["stays_in_week_nights"] + df["stays_in_weekend_nights"]
        df["departure_date"] = df["arrival_date"] + df["n_nights"].apply(pd.Timedelta, unit="D")
        df["total_transaction"] = df["n_nights"] * df["adr"]

        old_arrival_date_cols = [c for c in df.columns if c.startswith("arrival_date_")]
        df.drop(columns=old_arrival_date_cols, inplace=True)

    @staticmethod
    def add_is_last_minute_cancellation(df: pd.DataFrame):
        """
        Add a boolean column is_last_minute_cancellation.
        A reservation is said to be last minute cancellation if the reservation is cancelled on the day of the check-in.

        NB: arrival_date must be added in advance.
        """
        df["is_last_minute_cancellation"] = (df["reservation_status"] == "Canceled") & (
            df["arrival_date"] == df["reservation_status_date"]
        )

    @staticmethod
    def add_actual_departure_date(df: pd.DataFrame):
        """
        Some lodgers can leave the hotel before the date of the planned departure date.
        If the reservation_status is "Check-Out", then reservation_status_date is the actual departure date.

        - Add a column actual_departure_date of the date of the actual departure date. If th
        - Add a column n_stay_actual of the number of actual stays.
        - Add a boolean column is_early_departure.
        """

        def actual_departure_date(row) -> Optional[pd.Timestamp]:
            if row["reservation_status"] == ReservationStatus.check_out.value:
                return row["reservation_status_date"]
            else:
                return None

        df["actual_departure_date"] = df.apply(actual_departure_date, axis=1)
        df["n_stay_actual"] = (df["actual_departure_date"] - df["arrival_date"]).apply(lambda x: x.days)
        df["is_early_departure"] = df["actual_departure_date"] < df["departure_date"]

    @staticmethod
    def add_meals(df: pd.DataFrame):
        """
        - Add a boolean column breakfast
        - Add a boolean column lunch
        - Add a boolean column dinner

        NB: "Undefined" is regarded as SC. (No meals)
        """
        meal2breakfast = {"BB": True, "HB": True, "FB": True, "SC": False}
        meal2lunch = {"BB": False, "HB": False, "FB": True, "SC": False}
        meal2dinner = {"BB": False, "HB": True, "FB": True, "SC": False}

        df["breakfast"] = df["meal"].map(meal2breakfast)
        df["lunch"] = df["meal"].map(meal2lunch)
        df["dinner"] = df["meal"].map(meal2dinner)

    @staticmethod
    def convert_country_for_human(df: pd.DataFrame):
        """
        - Convert country codes into ordinary descriptions of countries
        """
        code2country = load_country_code_mapping()
        df["country"] = df["country"].apply(lambda x: code2country.get(x, x))

    @classmethod
    def apply_all(cls, data_raw: pd.DataFrame):
        df = data_raw.copy()

        cls.convert_data_type(df)
        cls.remove_invalid_records(df)
        cls.add_arrival_date(df)
        cls.add_is_last_minute_cancellation(df)
        cls.add_actual_departure_date(df)
        cls.add_meals(df)

        return df


def main():
    df_hotel_raw = load_raw_hotel_data()
    df_hotel_cleaned = Preprocessor.apply_all(df_hotel_raw)

    df_hotel_cleaned.to_parquet(bookings_data_path)
    print(f"SAVED: {bookings_data_path} ({len(df_hotel_cleaned)} rows)")


if __name__ == "__main__":
    main()
