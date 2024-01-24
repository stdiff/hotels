import altair as alt
import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.aggregations import compute_occupancy_rate
from hotels.dashboard import draw_daily_kpi_with_quoters
from hotels.models import Hotel, TimeGranularity, TUTransform


def compute_sales_by_day(df_booking: pd.DataFrame, df_actions: pd.DataFrame) -> pd.DataFrame:
    """
    :return: DataFrame[hotel, date, room_type, sales]
    """
    df_adr_corrected = df_booking.assign(sales=lambda x: x["adr"] * x["n_nights"] / x["n_stay_actual"])[
        ["hotel", "reservation_id", "assigned_room_type", "sales"]
    ].rename(columns={"assigned_room_type": "room_type"})

    df_sales = (
        df_actions.merge(df_adr_corrected)
        .query("action != 'departure'")
        .groupby(["hotel", "date", "room_type"], as_index=False)["sales"]
        .sum()
    )
    return df_sales


def show_sales_tab(
    df_booking: pd.DataFrame,
    df_actions: pd.DataFrame,
    df_room_usage: pd.DataFrame,
    df_room_count: pd.DataFrame,
    hotel: Hotel,
):
    st.header("Sales")

    selected_time_granularity = st.selectbox(
        "Time granularity", list(TimeGranularity), index=0, format_func=lambda g: g.value, key="a"
    )
    tu_transform = TUTransform.from_time_granularity(selected_time_granularity)

    df_sales = (
        compute_sales_by_day(df_booking, df_actions)
        .query("hotel == @hotel")
        .query("@data_start_date <= date <= @data_end_date_incl")
    )

    chart = draw_daily_kpi_with_quoters(
        df_sales.groupby("date")["sales"].sum().reset_index(), tu_transform=tu_transform
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Revenue Per Occupied Room")

    df_rev_por = (
        df_sales.merge(df_room_usage)
        .groupby("date")[["sales", "n_occupied_rooms"]]
        .sum()
        .assign(RevPOR=lambda x: x["sales"] / x["n_occupied_rooms"])
        .reset_index()
    )

    chart = draw_daily_kpi_with_quoters(
        df_rev_por[["date", "RevPOR"]], tu_transform=tu_transform, kpi_is_proportion=False
    )
    st.altair_chart(chart, use_container_width=True)
    # st.dataframe(df_rev_por, use_container_width=True)
