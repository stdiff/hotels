import datetime as dt

import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import set_page_config
from hotels.models import Hotel, TimeGranularity, TUTransform
from hotels.load_data import load_booking_data, load_action_data

from pages.tab.hotel_usage import show_hotel_usage_tab
from pages.tab.marketing import show_marketing_tab
from pages.tab.sales import show_sales_tab
from pages.tab.cancallations import show_cancellation_tab

set_page_config()


@st.cache_data
def load_data(hotel: Hotel) -> (pd.DataFrame, pd.DataFrame):
    df_booking = load_booking_data().query("hotel == @hotel")
    prefix = "C" if hotel == Hotel.city_hotel else "R"

    df_actions = load_action_data()
    df_actions = df_actions[df_actions["reservation_id"].str.startswith(prefix)]

    return df_booking, df_actions


@st.cache_data
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
    st.title("Internal Dashboards")

    with st.sidebar:
        st.subheader("Hotel")
        selected_hotel = st.radio(
            label="hotel", options=list(Hotel), index=0, format_func=lambda h: h.value, label_visibility="collapsed"
        )
        st.subheader("Time granularity")
        selected_time_granularity = st.radio(
            "Time granularity",
            list(TimeGranularity),
            index=0,
            format_func=lambda g: g.value,
            key="time-granularity",
            label_visibility="collapsed",
        )
        tu_transform = TUTransform.from_time_granularity(selected_time_granularity)

    df_booking, df_actions = load_data(selected_hotel)
    df_room_usage = aggregate_room_usage(df_booking, df_actions)
    df_room_count = count_rooms(df_room_usage)

    hotel_usage_tab, sales_tab, marketing_tab, cancellations_tab = st.tabs(
        ["Hotel Usage", "Sales", "Marketing", "Cancellations"]
    )

    with hotel_usage_tab:
        show_hotel_usage_tab(df_booking, df_actions, df_room_usage, df_room_count, tu_transform)

    with sales_tab:
        show_sales_tab(df_booking, df_actions, df_room_usage, tu_transform)

    with marketing_tab:
        show_marketing_tab(df_booking, df_actions, tu_transform)

    with cancellations_tab:
        show_cancellation_tab(df_booking, tu_transform)


if __name__ == "__main__":
    show_dashboard()
