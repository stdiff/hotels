import altair as alt
import numpy as np
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
    st.subheader("Cancellation Rate by Lead Time", help="The time granularity is not applied.")

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


def draw_no_show_counts_by_day(df_booking: pd.DataFrame, tu_transform: TUTransform):
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
        if key == "total_count":
            col.metric(key, value)
        else:
            col.metric(key, value, help="statistics by day")

    chart = (
        alt.Chart(df_count_no_show)
        .mark_bar()
        .encode(
            x=f"{tu_transform}(arrival_date)",
            y=alt.Y("sum(count)").title("count"),
            tooltip=[
                alt.Tooltip(f"{tu_transform}(arrival_date)", title="Arrival date"),
                alt.Tooltip("min(arrival_date)", title="Arrival date from"),
                alt.Tooltip("max(arrival_date)", title="Arrival date to"),
                alt.Tooltip("sum(count)", title="no-show count"),
            ],
        )
    )
    st.altair_chart(chart, use_container_width=True)


def draw_cohort_analysis_for_survival_rate(df_booking: pd.DataFrame):
    st.subheader("Survival Rate")

    st.markdown(
        """
    - The survival rate is the proportion of non-cancelled reservations. i.e. Survival rate + Cancellation Rate = 100% 
    - This rate varies over time until the status of all reservations are fixed. 
    
    **How to read the following heatmap**
    
    - lead time cohort: cohorts of reservations by lead time. 
      Cohort 0: lead time = 0, Cohort 1: lead time is between 1 to 7, Cohort 2: lead time is between 8 to 14, ...
    - time elapsed: how long had elapsed since the reservation was made. bin 0: 0 day. bin 1: 1 to 7 days, bin 2: 8 to 14 days, ...
    
    **Observations**
    
    - If the reservation is made on the arrival day, then less than 9% of the reservations are cancelled. 
    - The survival rate is smaller than 60% if the lead time is longer than 84 days. (lead time cohort number &geq; 13.)
    """
    )
    r_cancellation_rate = df_booking["is_canceled"].mean()
    survival_rate = 1 - r_cancellation_rate
    st.metric("survival rate (final state)", f"{survival_rate:0.2%}")

    df_survival_rate = df_booking[
        ["is_canceled", "lead_time", "reservation_status_date", "reservation_date", "arrival_date"]
    ].assign(
        time_elapsed=lambda x: (x["reservation_status_date"] - x["reservation_date"]).dt.days,
        lead_time_cohort=lambda x: (x["lead_time"] + 6) // 7,
        time_elapsed_bin=lambda x: (x["time_elapsed"] + 6) // 7,
    )

    def _compute_survival_date(data: pd.DataFrame) -> pd.DataFrame:
        lead_time_cohort = data["lead_time_cohort"].iloc[0]
        n_reservations = len(data)
        gb = data.query("is_canceled == 1").groupby(["lead_time_cohort", "time_elapsed_bin"])

        df = gb.agg(
            n_cancel=("lead_time", "size"),
            min_time_elapsed=("time_elapsed", "min"),
            max_time_elapsed=("time_elapsed", "max"),
            min_lead_time=("lead_time", "min"),
            max_lead_time=("lead_time", "max"),
        ).reset_index()

        df = (
            pd.DataFrame({"lead_time_cohort": lead_time_cohort, "time_elapsed_bin": range(0, lead_time_cohort + 1)})
            .merge(df, how="left")
            .fillna({"n_cancel": 0})
            .sort_values(by="time_elapsed_bin")
            .assign(cumsum_cancel=lambda x: x["n_cancel"].cumsum())
        )

        df["survival_rate"] = 1 - df["cumsum_cancel"] / n_reservations
        return df

    df_survival_rate = (
        df_survival_rate.groupby("lead_time_cohort", as_index=False)
        .apply(_compute_survival_date)
        .reset_index(drop=True)
    )

    chart_survival_rate_base: alt.Chart = (
        alt.Chart(df_survival_rate)
        .transform_filter(alt.datum.lead_time_cohort <= 30)
        .encode(
            x=alt.X("time_elapsed_bin:O").title("Time Elapsed (binned)").axis(labelAngle=0),
            y=alt.Y("lead_time_cohort:O").title("Lead Time Cohort"),
            tooltip=[
                alt.Tooltip("lead_time_cohort", title="Lead Time Cohort"),
                alt.Tooltip("min_lead_time", title="Lead Time from"),
                alt.Tooltip("max_lead_time", title="Lead Time to"),
                alt.Tooltip("time_elapsed_bin", title="Time Elapsed Bin Nr"),
                alt.Tooltip("min_time_elapsed", title="min time elapsed"),
                alt.Tooltip("max_time_elapsed", title="max time elapsed"),
                alt.Tooltip("survival_rate", title="Survival Rate", format="0.1%"),
            ],
        )
    )

    chart_survival_rate_heatmap = chart_survival_rate_base.mark_rect(opacity=0.7).encode(
        color=alt.Color("survival_rate")
        .scale(scheme="redblue", reverse=False, domainMid=survival_rate)
        .legend(orient="top-right", format="%", title="Survival Rate")
    )

    chart_survival_rate_text = (
        chart_survival_rate_base.transform_filter(alt.datum.lead_time_cohort == alt.datum.time_elapsed_bin)
        .mark_text()
        .encode(
            text=alt.Text("survival_rate", format="0.1%"),
            color=alt.condition(alt.datum.survival_rate < 0.5, alt.value("white"), alt.value("black")),
        )
    )

    chart_survival_rate = chart_survival_rate_heatmap + chart_survival_rate_text
    st.altair_chart(chart_survival_rate, use_container_width=True)


def show_cancellation_tab(df_booking: pd.DataFrame, tu_transform: TUTransform):
    st.header("Cancellations")
    df_cancellations = compute_cancellation_rate_by_day(df_booking)
    draw_cancellation_counts(df_cancellations, tu_transform)
    draw_cancellation_rate_by_country(df_booking)
    draw_cancellation_rate_by_lead_time(df_booking, upper_limit=365)
    draw_cohort_analysis_for_survival_rate(df_booking)
    draw_no_show_counts_by_day(df_booking, tu_transform)
