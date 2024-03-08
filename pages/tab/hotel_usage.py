import altair as alt
import pandas as pd
import streamlit as st

from hotels.dashboard import draw_daily_kpi_with_quoters
from hotels.models import TUTransform


@st.cache_data
def compute_occupancy_rate_by_room_type(df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame) -> pd.DataFrame:
    """
    PK = (hotel, date, room_type)
    :return: DataFrame[hotel, date, room_type, n_occupied_rooms, n_available_rooms, occupancy_rate]
    """
    df_occupancy_rate_by_room_type = df_room_usage.merge(df_room_count).assign(
        occupancy_rate=lambda x: x["n_occupied_rooms"] / x["n_rooms"]
    )
    return df_occupancy_rate_by_room_type


@st.cache_data
def compute_occupancy_rate(df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame) -> pd.DataFrame:
    """
    PK = (hotel, date)

    :return: DataFrame[hotel, date, n_occupied_rooms, n_available_rooms, occupancy_rate]
    """
    df_occupancy_rate = (
        df_room_usage.groupby(["hotel", "date"], as_index=False)["n_occupied_rooms"]
        .sum()
        .merge(df_room_count.groupby("hotel")["n_rooms"].sum().rename("n_available_rooms").reset_index())
        .assign(occupancy_rate=lambda x: x["n_occupied_rooms"] / x["n_available_rooms"])
    )
    return df_occupancy_rate


def show_occupancy_timeline(df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame, tu_transform: TUTransform):
    st.subheader("Occupancy Rate")

    df_occupancy_rate = compute_occupancy_rate(df_room_usage, df_room_count)

    chart_occupancy_rate = draw_daily_kpi_with_quoters(
        df_occupancy_rate[["date", "occupancy_rate"]], tu_transform, kpi_is_proportion=True
    )
    st.altair_chart(chart_occupancy_rate, use_container_width=True)

    st.subheader("Occupancy Rate by Room Type")
    st.markdown("You can highlight one of room types by clicking its legend. Deselect can be done by")
    df_occupancy_rate_by_room_type = compute_occupancy_rate_by_room_type(df_room_usage, df_room_count)

    room_types = sorted(df_occupancy_rate_by_room_type["room_type"].drop_duplicates())
    select_room_type = alt.selection_point(name="occupancy_timeline_selector", fields=["room_type"], bind="legend")
    nearest = alt.selection_point(on="mouseover", nearest=True, empty=False, fields=["x", "y"])
    chart_base: alt.Chart = (
        alt.Chart(df_occupancy_rate_by_room_type)
        .encode(
            x=alt.X(f"{tu_transform}(date)").title("date"),
            y=alt.Y("mean(occupancy_rate)").title("occupancy rate").axis(format="%"),
            color=alt.Color("room_type").scale(domain=room_types),
            opacity=alt.condition(select_room_type, alt.value(1.0), alt.value(0.1)),
            tooltip=[
                alt.Tooltip("room_type", title="Room Type"),
                alt.Tooltip(f"{tu_transform}(date)"),
                alt.Tooltip(f"min(date)", title="Start date"),
                alt.Tooltip(f"max(date)", title="End date"),
                alt.Tooltip(f"mean(occupancy_rate)", title="Occupancy Rate", format="0.1%"),
            ],
        )
        .add_params(select_room_type)
    )

    chart_lines = chart_base.mark_line()
    chart_layer = chart_base.mark_point().encode(opacity=alt.value(0)).add_params(nearest)
    st.altair_chart(chart_lines + chart_layer, use_container_width=True)


def show_number_of_guests(df_actions: pd.DataFrame, df_booking: pd.DataFrame, tu_transform: TUTransform):
    st.subheader("Number of guests staying at night")

    df_n_guests = (
        df_actions.merge(df_booking[["reservation_id", "n_lodgers", "hotel"]])
        .query("action != 'departure'")
        .groupby("date", as_index=False)["n_lodgers"]
        .sum()
    )  # DataFrame[date, n_lodgers]

    chart_n_guests = draw_daily_kpi_with_quoters(
        df_n_guests[["date", "n_lodgers"]].rename(columns={"n_lodgers": "number of guests"}),
        tu_transform=tu_transform,
        kpi_is_proportion=False,
    )
    st.altair_chart(chart_n_guests, use_container_width=True)


def show_parking_spaces_usage(df_booking: pd.DataFrame, df_actions: pd.DataFrame, tu_transform: TUTransform):
    st.subheader("Parking space usage")

    measure_field = "required_car_parking_spaces"
    df_parking_spaces = (
        df_actions.merge(df_booking[["reservation_id", measure_field, "hotel"]])
        .query("action != 'departure'")
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
    tu_transform: TUTransform,
):
    st.header("Hotel Usage")
    st.markdown("""Showing the average usage of the hotel by day""")

    show_occupancy_timeline(df_room_usage, df_room_count, tu_transform)
    show_number_of_guests(df_actions, df_booking, tu_transform)
    show_parking_spaces_usage(df_booking, df_actions, tu_transform)
