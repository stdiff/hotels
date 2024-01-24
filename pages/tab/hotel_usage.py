import pandas as pd
import streamlit as st

from hotels.aggregations import compute_occupancy_rate
from hotels.dashboard import draw_daily_kpi_with_quoters
from hotels.models import Hotel, TimeGranularity, TUTransform


def show_occupancy_timeline(
    df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame, hotel: Hotel, tu_transform: TUTransform
):
    st.subheader("Occupancy Rate")

    df_occupancy_rate = compute_occupancy_rate(df_room_usage, df_room_count, hotel)

    chart_occupancy_rate = draw_daily_kpi_with_quoters(
        df_occupancy_rate[["date", "occupancy_rate"]], tu_transform, kpi_is_proportion=True
    )
    st.altair_chart(chart_occupancy_rate, use_container_width=True)


def show_number_of_guests(df_actions: pd.DataFrame, df_booking: pd.DataFrame, hotel: Hotel, tu_transform: TUTransform):
    st.subheader("Number of guests staying at night")

    df_n_guests = (
        df_actions.merge(df_booking[["reservation_id", "n_lodgers", "hotel"]])
        .query("hotel == @hotel and action != 'departure'")
        .groupby("date", as_index=False)["n_lodgers"]
        .sum()
    )  # DataFrame[date, n_lodgers]

    chart_n_guests = draw_daily_kpi_with_quoters(
        df_n_guests[["date", "n_lodgers"]].rename(columns={"n_lodgers": "number of guests"}),
        tu_transform=tu_transform,
        kpi_is_proportion=False,
    )
    st.altair_chart(chart_n_guests, use_container_width=True)


def show_parking_spaces_usage(
    df_booking: pd.DataFrame, df_actions: pd.DataFrame, hotel: Hotel, tu_transform: TUTransform
):
    st.subheader("Parking space usage")

    measure_field = "required_car_parking_spaces"
    df_parking_spaces = (
        df_actions.merge(df_booking[["reservation_id", measure_field, "hotel"]])
        .query("hotel == @hotel and action != 'departure'")
        .groupby("date", as_index=False)[measure_field]
        .sum()
    )

    chart_parking_spaces = draw_daily_kpi_with_quoters(
        df_parking_spaces[["date", measure_field]], tu_transform=tu_transform, kpi_is_proportion=False
    )
    st.altair_chart(chart_parking_spaces, use_container_width=True)


def show_hotel_usage_tab(
    df_booking: pd.DataFrame,
    df_actions: pd.DataFrame,
    df_room_usage: pd.DataFrame,
    df_room_count: pd.DataFrame,
    selected_hotel: Hotel,
):
    st.header("Hotel Usage")
    st.markdown("""Showing the average usage of the hotel by day""")

    selected_time_granularity = st.selectbox(
        "Time granularity", list(TimeGranularity), index=0, format_func=lambda g: g.value
    )
    tu_transform = TUTransform.from_time_granularity(selected_time_granularity)

    show_occupancy_timeline(df_room_usage, df_room_count, selected_hotel, tu_transform)
    show_number_of_guests(df_actions, df_booking, selected_hotel, tu_transform)
    show_parking_spaces_usage(df_booking, df_actions, selected_hotel, tu_transform)
