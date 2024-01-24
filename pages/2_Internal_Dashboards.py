import datetime as dt

import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import set_page_config
from hotels.models import Hotel
from hotels.load_data import load_booking_data, load_action_data

from pages.tab.hotel_usage import show_hotel_usage_tab
from pages.tab.sales import show_sales_tab

set_page_config()


@st.cache_data(ttl="8h")
def load_data(hotel: Hotel) -> (pd.DataFrame, pd.DataFrame):
    df_booking = load_booking_data().query("hotel == @hotel")
    prefix = "C" if hotel == Hotel.city_hotel else "R"

    df_actions = load_action_data()
    df_actions = df_actions[df_actions["reservation_id"].str.startswith(prefix)]

    return df_booking, df_actions


@st.cache_data(ttl="8h")
def aggregate_room_usage(df_booking: pd.DataFrame, df_actions: pd.DataFrame) -> pd.DataFrame:
    """
    :param df_booking:
    :param df_actions:
    :return: DataFrame[hotel, room_type, date, n_occupied_rooms]
    """
    df_room_usage = (
        df_actions.merge(df_booking[["reservation_id", "assigned_room_type", "hotel"]])
        .query("action != 'departure'")
        .groupby(["hotel", "assigned_room_type"])["date"]
        .value_counts()
        .reset_index()
        .rename(columns={"count": "n_occupied_rooms", "assigned_room_type": "room_type"})
    )

    ## we have to fill 0 usage
    df_room_usage = (
        ## NB: this crossproduct is not good because the hotels have different room types.
        df_room_usage[["hotel", "room_type"]]
        .drop_duplicates()
        .merge(pd.date_range(data_start_date, data_end_date_incl, name="date").to_frame(), how="cross")
        .merge(df_room_usage, how="left")
        .fillna({"n_occupied_rooms": 0})
        .assign(n_occupied_rooms=lambda x: x["n_occupied_rooms"].astype(int))
    )

    return df_room_usage


def count_rooms(df_room_usage: pd.DataFrame) -> pd.DataFrame:
    """
    :param df_room_usage: DataFrame[hotel, room_type, n_occupied_rooms]
    :return: DataFrame[hotel, room_type, n_rooms]
    """
    df_room_count = (
        df_room_usage.groupby(["hotel", "room_type"])["n_occupied_rooms"].max().rename("n_rooms").reset_index()
    )
    return df_room_count


def show_dashboard():
    cols = st.columns(3)
    with cols[0]:
        selected_hotel = st.radio(label="hotel", options=list(Hotel), index=0, format_func=lambda h: h.value)

    with cols[1]:
        # todo: how do we go with this period?
        min_date, max_date = dt.date(2015, 10, 1), dt.date(2017, 8, 31)
        today = dt.date.today().replace(year=2016)
        selected_date = pd.to_datetime(
            st.date_input(label="date", value=today, min_value=min_date, max_value=max_date, format="YYYY-MM-DD")
        )

    with cols[2]:
        st.info(f"Any date between {min_date} and {max_date}")

    df_booking, df_actions = load_data(selected_hotel)
    df_room_usage = aggregate_room_usage(df_booking, df_actions)
    df_room_count = count_rooms(df_room_usage)

    overview_tab, hotel_usage_tab, sales_tab = st.tabs(["Overview", "Hotel Usage", "Sales"])

    with overview_tab:
        st.header("Overview")

        st.subheader("booking")
        st.dataframe(df_booking, use_container_width=True)

        st.subheader("actions")
        st.dataframe(df_actions, use_container_width=True)

        st.subheader("room usage")
        st.dataframe(df_room_usage, use_container_width=True)

        st.subheader("count rooms")
        st.dataframe(df_room_count, use_container_width=True)

    with hotel_usage_tab:
        show_hotel_usage_tab(df_booking, df_actions, df_room_usage, df_room_count, selected_hotel)

    with sales_tab:
        show_sales_tab(df_booking, df_actions, df_room_usage, df_room_count, selected_hotel)


if __name__ == "__main__":
    show_dashboard()
