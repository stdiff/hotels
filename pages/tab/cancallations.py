import numpy as np
import altair as alt
import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.models import TUTransform
from hotels.load_data import load_country_code_mapping


def compute_cancellation_rate_by_day(df_booking: pd.DataFrame) -> pd.DataFrame:
    """
    :return: DataFrame[arrival_date, cancelled, checked-in, n_reservations, r_cancellation]
    """
    df_cancellations = (
        df_booking.query("@data_start_date <= arrival_date <= @data_end_date_incl")
        .groupby("arrival_date")
        .apply(compute_cancellation_rate)
        .reset_index()
    )
    return df_cancellations


def compute_cancellation_rate_by_country(df_booking: pd.DataFrame) -> pd.DataFrame:
    country_mapping = load_country_code_mapping()

    df_cancellations = (
        df_booking.query("@data_start_date <= arrival_date <= @data_end_date_incl")
        .groupby("country")
        .apply(compute_cancellation_rate)
        .reset_index()
        .assign(country=lambda x: x["country"].apply(lambda x: country_mapping.get(x, x)))
    )
    return df_cancellations


def compute_cancellation_rate(data: pd.DataFrame) -> pd.Series:
    """
    :return: Series[arrival_date, cancelled, checked-in, n_reservations, r_cancellation]
    """
    n_checked_in = len(data.query("is_canceled == 0"))
    n_cancelled = len(data.query("is_canceled == 1"))
    n_reservations = n_checked_in + n_cancelled
    r_cancellation = n_cancelled / n_reservations

    return pd.Series(
        {
            "cancelled": n_cancelled,
            "checked-in": n_checked_in,
            "n_reservations": n_reservations,
            "r_cancellation": r_cancellation,
        }
    )


def draw_cancellation_counts(df_cancellations: pd.DataFrame, tu_transform: TUTransform):
    """
    :param df_cancellations: DataFrame[arrival_date, cancelled, checked-in, n_reservations, r_cancellation]
    """
    st.subheader("Cancellation counts (bars) and cancellation rate (dashed line)")

    n_reservations = df_cancellations["n_reservations"].sum()
    n_cancelled = df_cancellations["cancelled"].sum()

    cols = st.columns(3)
    cols.pop(0).metric("Number of reservations", n_reservations)
    cols.pop(0).metric("Number of cancellations", n_cancelled)
    cols.pop(0).metric("Cancellation rate", f"{n_cancelled/n_reservations:0.1%}")

    chart_base: alt.Chart = (
        alt.Chart(df_cancellations)
        .transform_timeunit(date=f"{tu_transform}(arrival_date)")
        .transform_aggregate(
            total_checked_in="sum(checked-in)",
            total_cancellations="sum(cancelled)",
            total_reservations="sum(n_reservations)",
            min_date="min(arrival_date)",
            max_date="max(arrival_date)",
            groupby=["date"],
        )
        .transform_calculate(cancellation_rate="datum.total_cancellations / datum.total_reservations")
        .encode(
            x=f"date:T",
            tooltip=[
                alt.Tooltip("min_date:T", title="period starts from"),
                alt.Tooltip("max_date:T", title="period ends on"),
                "total_checked_in:Q",
                "total_cancellations:Q",
                alt.Tooltip("cancellation_rate:Q", format="0.1%"),
            ],
        )
    )

    chart_count = chart_base.mark_bar(opacity=0.6).encode(y="total_cancellations:Q")
    chart_rate = chart_base.mark_line(size=1, strokeDash=[5, 5], color="black").encode(
        y=alt.Y("cancellation_rate:Q").axis(format="%")
    )

    tooltip_selector = alt.selection_point(fields=["x"], on="mouseover", nearest=True, empty=False)
    chart = (chart_count + chart_rate).resolve_scale(y="independent").add_params(tooltip_selector)
    st.altair_chart(chart, use_container_width=True)


def draw_cancellation_rate_by_country(df_booking: pd.DataFrame):
    st.subheader("Cancellation Rate by country (with &geq; 100 reservations)", help="")
    df_cancellations_by_country = compute_cancellation_rate_by_country(df_booking).query("n_reservations >= 100")

    chart_base: alt.Chart = alt.Chart(df_cancellations_by_country).encode(
        x=alt.X("r_cancellation").title("Cancellation Rate").axis(format="%"),
        y=alt.Y("country:N", sort="-x").axis(None),
        color=alt.Color("r_cancellation").scale(scheme="turbo", domainMin=0, domainMax=1).legend(None),
        tooltip=[
            "country",
            alt.Tooltip("n_reservations", title="Total Reservations"),
            alt.Tooltip("cancelled", title="Total Cancellations"),
            alt.Tooltip("r_cancellation", title="Cancellation Rate", format="0.1%"),
        ],
    )
    chart_bar = chart_base.mark_bar()
    chart_text = chart_base.mark_text(angle=0, size=14, dx=4, align="left").encode(
        text=alt.X("country"), color=alt.value("#000000")
    )
    chart = chart_bar + chart_text

    st.altair_chart(chart, use_container_width=True)


def draw_cancellation_rate_by_lead_time(df_booking: pd.DataFrame, upper_limit: int):
    st.subheader("Cancellation Rate by Lead Time")

    df_truncated = df_booking.query("lead_time <= @upper_limit")
    df = pd.crosstab(df_truncated["lead_time"], df_truncated["is_canceled"]).reset_index()
    df.rename(columns={0: "n_checked_in", 1: "n_cancel"}, inplace=True)
    df["total"] = df["n_checked_in"] + df["n_cancel"]
    df["r_cancel"] = df["n_cancel"] / df["total"]

    chart_base: alt.Chart = alt.Chart(df).encode(
        x=alt.X("lead_time").title("Lead Time").scale(domainMin=0, domainMax=upper_limit),
        y=alt.Y("r_cancel").axis(format="%").title("Cancellation Rate"),
        tooltip=[
            alt.Tooltip("lead_time").title("Lead Time (in days)"),
            alt.Tooltip("r_cancel", format="0.2%", title="Cancellation Rate"),
            alt.Tooltip("total", title="Number of reservations"),
        ],
    )
    chart_line = chart_base.mark_line(point=False)
    chart_tooltip = chart_base.mark_line(point=False, opacity=0.0, size=10)
    chart = chart_line + chart_tooltip
    st.altair_chart(chart, use_container_width=True)


def draw_no_show_counts_by_day(df_booking: pd.DataFrame):
    st.subheader("No show counts")

    df_count_no_show = pd.merge(
        pd.date_range(data_start_date, data_end_date_incl, name="arrival_date").to_frame().reset_index(drop=True),
        df_booking.query("reservation_status == 'No-Show'")["arrival_date"].value_counts().reset_index(),
        on="arrival_date",
        how="left",
    ).fillna({"count": 0})

    s_metric = df_count_no_show.agg(
        total_count=("count", "sum"), minimum=("count", "min"), median=("count", "median"), maximum=("count", "max")
    )["count"]

    for (key, value), col in zip(s_metric.items(), st.columns(len(s_metric))):
        col.metric(key, value)

    chart = alt.Chart(df_count_no_show).mark_bar().encode(x="arrival_date", y="count")
    st.altair_chart(chart, use_container_width=True)


def show_cancellation_tab(df_booking: pd.DataFrame):
    st.header("Cancellations")

    tu_transform = TUTransform.yearweek
    df_cancellations = compute_cancellation_rate_by_day(df_booking)
    draw_cancellation_counts(df_cancellations, tu_transform)
    draw_cancellation_rate_by_country(df_booking)
    draw_cancellation_rate_by_lead_time(df_booking, upper_limit=365)
    draw_no_show_counts_by_day(df_booking)
