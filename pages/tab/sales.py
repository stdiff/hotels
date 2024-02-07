import altair as alt
import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import draw_daily_kpi_with_quoters, draw_kpi_by_cat
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

    # room_types = sorted(df_rev_por_by_room_type["room_type"].drop_duplicates())
    # select_room_type = alt.selection_point(fields=["room_type"], bind="legend")
    # nearest = alt.selection_point(on="mouseover", nearest=True, empty=False, fields=["x", "y"])
    #
    # chart_base: alt.Chart = (
    #     alt.Chart(df_rev_por_by_room_type)
    #     .encode(
    #         x=f"{tu_transform}(date)",
    #         y="mean(RevPOR)",
    #         color=alt.Color("room_type:N").scale(domain=room_types),
    #         opacity=alt.condition(select_room_type, alt.value(1.0), alt.value(0.1)),
    #         tooltip=[
    #             alt.Tooltip("room_type", title="Room Type"),
    #             alt.Tooltip(f"{tu_transform}(date)"),
    #             alt.Tooltip(f"min(date)", title="Start date"),
    #             alt.Tooltip(f"max(date)", title="End date"),
    #             alt.Tooltip("mean(RevPOR)", format="0.2f", title="Avg RevPOR by day"),
    #             alt.Tooltip("mean(sales)", format="0.2f", title="Avg Sales by day"),
    #             alt.Tooltip("mean(n_occupied_rooms)", format="0.1f", title="Avg sold rooms by day"),
    #         ],
    #     )
    #     .add_params(select_room_type)
    # )
    # chart_rev_por_by_room_type = chart_base.mark_line()
    # chart_layer = chart_base.mark_point().encode(opacity=alt.value(0)).add_params(nearest)
    #
    # st.altair_chart(chart_rev_por_by_room_type + chart_layer, use_container_width=True)
