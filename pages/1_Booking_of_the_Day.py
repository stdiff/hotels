import datetime as dt

import pandas as pd
import streamlit as st
import altair as alt

from hotels.dashboard import set_page_config
from hotels.data_retrieval import load_raw_data, min_date, max_date
from hotels.data_processing import Preprocessor
from hotels.models import Hotel, ReservationStatus


@st.cache_data
def load_processed_booking_data() -> pd.DataFrame:
    df = load_raw_data()
    return Preprocessor.apply_all(df)


def pick_stayed_lodgers(hotel: Hotel, date: dt.date, df_raw: pd.DataFrame) -> pd.DataFrame:
    df = (
        df_raw.query("hotel == @hotel.value")
        .query("is_canceled == 0")
        .query("arrival_date <= @date < actual_departure_date")
        .drop(columns=["hotel", "is_canceled"])
    )
    return df


def draw_age_groups(df: pd.DataFrame) -> alt.Chart:
    """
    :param df: DataFrame[adults, children, babies]
    :return: bar chart of numbers of people by age group
    """
    df_age_groups = (
        df[["adults", "children", "babies"]]
        .sum()
        .rename("number of lodgers")
        .reset_index()
        .rename({"index": "age group"}, axis=1)
    )
    order = ["adults", "children", "babies"]
    chart = (
        alt.Chart(df_age_groups)
        .mark_bar()
        .encode(
            x=alt.X("age group", sort=order, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("number of lodgers"),
            color=alt.Color("age group", sort=order, legend=None),
            tooltip=df_age_groups.columns.to_list(),
        )
    )
    return chart


def draw_country_counts(df: pd.DataFrame, top_n: int = 5) -> alt.Chart:
    """
    :param df: DataFrame[country, n_lodgers]
    :param top_n: countries under this number will be consolidated
    :return:
    """
    df_country = (
        df.groupby("country", as_index=False)["n_lodgers"]
        .sum()
        .assign(
            r_lodgers=lambda x: x["n_lodgers"] / x["n_lodgers"].sum(),
            rank=lambda x: x["n_lodgers"].rank(method="min", ascending=False),
        )
    )

    if df_country["rank"].max() > top_n:
        df_country = pd.concat(
            [
                df_country.query("rank <= @top_n"),
                df_country.query("rank > @top_n")[["n_lodgers", "r_lodgers"]]
                .sum()
                .to_frame()
                .T.assign(rank=top_n + 1, country="OTHER"),
            ],
            axis=0,
        )

    order = df_country.sort_values(by="rank", ascending=True)["country"].to_list()

    chart = (
        alt.Chart(df_country)
        .mark_bar()
        .encode(
            x=alt.X("country", sort=order, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("n_lodgers", title="number of lodgers"),
            color=alt.Color("country", sort=order, legend=None),
            tooltip=[
                "country",
                alt.Tooltip("n_lodgers", title="number of lodgers"),
                alt.Tooltip("r_lodgers", title="proportion", format="0.2%"),
            ],
        )
    )
    return chart


def draw_room_type_counts(df: pd.DataFrame, room_type_column: str = "assigned_room_type") -> alt.Chart:
    """
    :param df: DataFrame[assigned_room_type, adults, children, babies, n_lodgers, checkout]
    :param room_type_column: column name of the room type
    :return: bar chart of number of rooms (reservations) by room type
    """
    gb_room_type = df.groupby(room_type_column)

    columns = [
        gb_room_type.size().rename("number of rooms"),
        gb_room_type["adults"].sum(),
        gb_room_type["children"].sum(),
        gb_room_type["babies"].sum(),
        gb_room_type["n_lodgers"].sum(),
    ]
    if "checkout" in df.columns:
        columns.append(gb_room_type["checkout"].sum())

    df_room_types = pd.concat(columns, axis=1).reset_index()

    chart_room_type = (
        alt.Chart(df_room_types)
        .mark_bar()
        .encode(
            x=alt.X(room_type_column, axis=alt.Axis(labelAngle=0)),
            y="number of rooms",
            color=alt.Color(room_type_column, legend=None),
            tooltip=df_room_types.columns.to_list(),
        )
    )
    return chart_room_type


def show_lodgers_from_yesterday_tab(hotel: Hotel, date: dt.date, df_raw: pd.DataFrame):
    st.header("Lodgers from yesterday")

    st.markdown(
        """
    Statistics about the lodgers who stayed last night.
    Number of meals is the number of people who booked the meal (breakfast, lunch, dinner) 
    """
    )

    yesterday = date - dt.timedelta(days=1)
    df_stayed = pick_stayed_lodgers(hotel, yesterday, df_raw)
    df_stayed["checkout"] = df_stayed["actual_departure_date"] == pd.to_datetime(date)
    n_guests_from_yesterday = int(df_stayed["n_lodgers"].sum())

    n_checkout = df_stayed["checkout"].sum()
    n_breakfast = int((df_stayed["breakfast"] * df_stayed["n_lodgers"]).sum())
    n_lunch = int((df_stayed["lunch"] * df_stayed["n_lodgers"] * ~df_stayed["checkout"]).sum())
    n_dinner = int((df_stayed["dinner"] * df_stayed["n_lodgers"] * ~df_stayed["checkout"]).sum())

    cols = st.columns(6)
    cols.pop(0).metric(label="Number of used rooms", value=len(df_stayed))
    cols.pop(0).metric(label="Number of lodgers", value=n_guests_from_yesterday)
    cols.pop(0).metric(label="Number of check-out", value=n_checkout)
    cols.pop(0).metric(label="Number of breakfast", value=n_breakfast)
    cols.pop(0).metric(label="Number of lunch", value=n_lunch)
    cols.pop(0).metric(label="Number of dinner", value=n_dinner)

    cols = st.columns(3)
    with cols.pop(0):
        st.subheader("Age groups")
        st.altair_chart(draw_age_groups(df_stayed), use_container_width=True)

    with cols.pop(0):
        st.subheader("Countries")
        st.altair_chart(draw_country_counts(df_stayed), use_container_width=True)

    with cols.pop(0):
        st.subheader("Used Room Types")
        st.altair_chart(draw_room_type_counts(df_stayed), use_container_width=True)


def pick_arriving_guests(hotel: Hotel, date: dt.date, df_raw: pd.DataFrame) -> pd.DataFrame:
    cancel_str = ReservationStatus.canceled.value
    df = (
        df_raw.query("hotel == @hotel.value")
        .query("arrival_date == @date")
        .query("reservation_status != @cancel_str or is_last_minute_cancellation")
        .drop(columns=["hotel", "arrival_date"])
    )
    return df


def show_new_arrivals_tab(hotel: Hotel, date: dt.date, df_raw: pd.DataFrame):
    st.header(f"Lodgers who arrive on {date}")
    st.markdown(
        """
    Statistics about the reservations whose check-in date is the given date.
    These numbers can contain no-show and/or last minute cancellation (i.e. cancellation on the check-in day).   
    """
    )

    df_arrivals = pick_arriving_guests(hotel, date, df_raw)
    n_new_lodgers = int(df_arrivals["n_lodgers"].sum())
    n_dinner = int((df_arrivals["dinner"] * df_arrivals["n_lodgers"]).sum())

    cols = st.columns([1, 3])
    with cols[0]:
        st.metric(label="Number of check-in", value=len(df_arrivals))
        st.metric(label="Number of new lodgers", value=n_new_lodgers)
        st.metric(label="Number of dinner", value=n_dinner)

    with cols[1]:
        st.subheader("Reserved room types")
        st.altair_chart(draw_room_type_counts(df_arrivals, "reserved_room_type"), use_container_width=True)


def show_staying_lodgers_tab(hotel: Hotel, date: dt.date, df_raw: pd.DataFrame):
    st.header("Staying Lodgers")
    st.markdown(
        """
    Statistics of the lodgers who stayed at night of the day.
     
    - We also see the change between the bookings and the actual hotel usage such as number of no-shows. 
    - [Definition of Average Daily Rate (ADR)](https://www.investopedia.com/terms/a/average-daily-rate.asp)
    """
    )

    df_arrived = pick_arriving_guests(hotel, date, df_raw)

    col_metrics, col_chart = st.columns([3, 2])

    with col_metrics:
        n_check_in = (df_arrived["reservation_status"] == ReservationStatus.check_out.value).sum()
        n_no_show = (df_arrived["reservation_status"] == ReservationStatus.no_show.value).sum()
        n_last_minute_cancellation = df_arrived["is_last_minute_cancellation"].sum()
        n_room_change = (df_arrived["reserved_room_type"] != df_arrived["assigned_room_type"]).sum()

        cols = st.columns(4)
        cols.pop(0).metric(label="Actual Check-Ins", value=n_check_in)
        cols.pop(0).metric(label="No-Shows", value=n_no_show)
        cols.pop(0).metric(label="Last Minute Cancellations", value=n_last_minute_cancellation)
        cols.pop(0).metric(label="Room Change Count", value=n_room_change)

        df_stay = pick_stayed_lodgers(hotel, date, df_raw)
        n_used_room = len(df_stay)
        revenue = df_stay["adr"].sum()
        adr = revenue / n_used_room
        cols = st.columns(3)
        cols.pop(0).metric(label="Used rooms", value=n_used_room)
        cols.pop(0).metric(label="Revenue", value=f"€{revenue:0.2f}")
        cols.pop(0).metric(label="Average Daily Rate", value=f"€{adr:0.2f}")

    with col_chart:
        st.subheader("Used room types")
        st.altair_chart(draw_room_type_counts(df_stay), use_container_width=True)


def dashboard():
    st.title("Booking of the Day")

    df_raw = load_processed_booking_data()

    with st.sidebar:
        st.subheader("Choose Hotel Type")
        selected_hotel = st.radio(
            label="hotel", options=list(Hotel), index=0, format_func=lambda h: h.value, label_visibility="collapsed"
        )

        st.subheader("Choose Date")
        selected_date = st.date_input(
            label="date",
            value=dt.date(2016, 1, 1),
            min_value=min_date,
            max_value=max_date,
            label_visibility="collapsed",
            format="YYYY-MM-DD",
        )
        st.info(f"Any date between {min_date} and {max_date}")

    lodgers_from_yesterday_tab, new_arrivals_tab, staying_lodgers_tab = st.tabs(
        ["Lodgers from yesterday", "New arrivals", "Staying lodgers"]
    )
    with lodgers_from_yesterday_tab:
        show_lodgers_from_yesterday_tab(selected_hotel, selected_date, df_raw)

    with new_arrivals_tab:
        show_new_arrivals_tab(selected_hotel, selected_date, df_raw)

    with staying_lodgers_tab:
        show_staying_lodgers_tab(selected_hotel, selected_date, df_raw)


if __name__ == "__main__":
    set_page_config()
    dashboard()
