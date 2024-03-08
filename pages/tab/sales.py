import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import draw_daily_kpi_with_quoters, draw_kpi_by_cat
from hotels.models import TUTransform


@st.cache_data
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
    tu_transform: TUTransform,
):
    st.header("Sales")

    df_sales = compute_sales_by_day(df_booking, df_actions).query("@data_start_date <= date <= @data_end_date_incl")

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

    st.subheader("RevPOR by Room Type")
    st.markdown("You can highlight one of room types by clicking its legend. Deselect can be done by ")
    df_rev_por_by_room_type = df_sales.merge(df_room_usage).assign(RevPOR=lambda x: x["sales"] / x["n_occupied_rooms"])

    chart_rev_por_by_room_type = draw_kpi_by_cat(
        df_rev_por_by_room_type.rename(
            columns={"room_type": "Room Type", "sales": "Sales", "n_occupied_rooms": "number of occupied rooms"}
        ),
        tu_transform,
        "Room Type",
        "RevPOR",
        "Sales",
        "number of occupied rooms",
    )
    st.altair_chart(chart_rev_por_by_room_type, use_container_width=True)
