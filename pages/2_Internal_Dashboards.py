import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from hotels.dashboard import set_page_config
from hotels.models import Hotel, TimeGranularity
from hotels.load_data import load_booking_data, load_action_data

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
        .merge(pd.date_range("2015-07-01", "2017-08-31", name="date").to_frame(), how="cross")
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


def draw_quartiles(x: pd.Series, y: pd.Series, text_format: str = "0.1f") -> alt.Chart:
    s_q = y.quantile(q=[0.25, 0.50, 0.75])
    chart_base = alt.Chart(s_q.to_frame().assign(x=x.min()))
    chart_vline = chart_base.mark_rule(color="black", strokeDash=[5, 5]).encode(y=s_q.name)
    chart_text = chart_base.mark_text(dy=-10, fontSize=14, align="left").encode(
        x="x", y=s_q.name, text=alt.Text(s_q.name, format=text_format)
    )
    return chart_vline + chart_text


def show_occupancy_timeline(df_room_usage: pd.DataFrame, df_room_count: pd.DataFrame, hotel: Hotel, tu_transform: str):
    st.subheader("Occupancy Rate")

    df_occupancy_rate = (
        df_room_usage.query("hotel == @hotel")
        .groupby(["hotel", "date"], as_index=False)["n_occupied_rooms"]
        .sum()
        .merge(df_room_count.groupby("hotel")["n_rooms"].sum().rename("n_available_rooms").reset_index())
        .assign(occupancy_rate=lambda x: x["n_occupied_rooms"] / x["n_available_rooms"])
    )  # DataFrame[hotel, date, n_available_rooms, occupancy_rate]

    n_rooms = df_room_count.query("hotel == @hotel")["n_rooms"].sum()
    total_occupancy_rate = df_occupancy_rate["occupancy_rate"].mean()
    q1, q2, q3 = df_occupancy_rate["occupancy_rate"].quantile([0.25, 0.5, 0.75])

    cols = st.columns(5)
    cols.pop(0).metric("Number of hotel rooms", n_rooms)
    cols.pop(0).metric("Occupancy Rate", f"{total_occupancy_rate:0.1%}", help="Occupancy rate of the whole period")
    cols.pop(0).metric("Q1 occupancy rate", f"{q1:0.1%}")
    cols.pop(0).metric("Q2 occupancy rate", f"{q2:0.1%}")
    cols.pop(0).metric("Q3 occupancy rate", f"{q3:0.1%}")

    # Since the total number of rooms is constant, so mean of the occupancy rate agrees with the occupancy
    chart_occupancy_rate = (
        alt.Chart(df_occupancy_rate)
        .mark_bar(opacity=0.7)
        .encode(
            x=alt.X(f"{tu_transform}(date)").title("date"),
            y=alt.Y("mean(occupancy_rate)").title("Occupancy Rate").axis(format="%").scale(domainMin=0, domainMax=1),
            color=alt.Color("mean(occupancy_rate)")
            .scale(scheme="spectral", reverse=True, domainMin=0, domainMax=1)
            .legend(format="%")
            .title("Occupancy Rate"),
            tooltip=[
                alt.Tooltip(f"{tu_transform}(date)", title="date"),
                alt.Tooltip(f"min(date)", title="Start date"),
                alt.Tooltip(f"max(date)", title="End date"),
                alt.Tooltip("mean(occupancy_rate)", title="Occupancy Rate", format="0.2%"),
                alt.Tooltip("mean(n_occupied_rooms)", title="Avg number of occupied rooms", format="0.1f"),
            ],
        )
    )
    chart_quantiles = draw_quartiles(
        x=df_occupancy_rate["date"], y=df_occupancy_rate["occupancy_rate"], text_format="0.1%"
    )
    st.altair_chart(chart_occupancy_rate + chart_quantiles, use_container_width=True)


def show_number_of_guests(df_actions: pd.DataFrame, df_booking: pd.DataFrame, hotel: Hotel, tu_transform: str):
    st.subheader("Number of guests staying at night")

    df_n_guests = (
        df_actions.merge(df_booking[["reservation_id", "n_lodgers", "hotel"]])
        .query("hotel == @hotel and action != 'departure'")
        .groupby("date", as_index=False)["n_lodgers"]
        .sum()
    )  # DataFrame[date, n_lodgers]

    cols = st.columns(4)
    cols.pop(0).metric("Avg. number of staying guests", f"{df_n_guests.n_lodgers.mean():0.1f}")
    cols.pop(0).metric("Q1 number of staying guests", df_n_guests["n_lodgers"].quantile(q=0.25))
    cols.pop(0).metric("Q2 number of staying guests", df_n_guests["n_lodgers"].quantile(q=0.50))
    cols.pop(0).metric("Q3 number of staying guests", df_n_guests["n_lodgers"].quantile(q=0.75))

    chart_guests = (
        alt.Chart(df_n_guests)
        .mark_bar(opacity=0.7)
        .encode(
            x=alt.X(f"{tu_transform}(date)").title("date"),
            y=alt.Y("mean(n_lodgers)").title("Number of guests"),
            color=alt.Color("mean(n_lodgers)").scale(scheme="spectral", reverse=True).title("Number of guests"),
            tooltip=[
                alt.Tooltip(f"{tu_transform}(date)", title="date"),
                alt.Tooltip(f"min(date)", title="Start date"),
                alt.Tooltip(f"max(date)", title="End date"),
                alt.Tooltip("mean(n_lodgers)", title="Daily Average"),
                alt.Tooltip("sum(n_lodgers)", title="Total number of guests"),
            ],
        )
    )
    chart_quantile = draw_quartiles(x=df_n_guests["date"], y=df_n_guests["n_lodgers"])

    st.altair_chart(chart_guests + chart_quantile, use_container_width=True)


def show_parking_spaces_usage(df_booking: pd.DataFrame, df_actions: pd.DataFrame, hotel: Hotel, tu_transform: str):
    st.subheader("Parking space usage")

    measure_field = "required_car_parking_spaces"
    df_parking_spaces = (
        df_actions.merge(df_booking[["reservation_id", measure_field, "hotel"]])
        .query("hotel == @hotel and action != 'departure'")
        .groupby("date", as_index=False)[measure_field]
        .sum()
    )

    cols = st.columns(4)
    cols.pop(0).metric("Avg. Required parking spaces", f"{df_parking_spaces[measure_field].mean():0.1f}")
    cols.pop(0).metric("Q1 Required parking spaces", df_parking_spaces[measure_field].quantile(q=0.25))
    cols.pop(0).metric("Q2 Required parking spaces", df_parking_spaces[measure_field].quantile(q=0.50))
    cols.pop(0).metric("Q3 Required parking spaces", df_parking_spaces[measure_field].quantile(q=0.75))

    chart_parking_spaces = (
        alt.Chart(df_parking_spaces)
        .mark_bar(opacity=0.7)
        .encode(
            x=alt.X(f"{tu_transform}(date)").title("date"),
            y=alt.Y(f"mean({measure_field})").title("Required parking spaces"),
            color=alt.Color(f"mean({measure_field})")
            .scale(scheme="spectral", reverse=True)
            .title("Required parking spaces"),
            tooltip=[
                alt.Tooltip(f"{tu_transform}(date)", title="date"),
                alt.Tooltip(f"min(date)", title="Start date"),
                alt.Tooltip(f"max(date)", title="End date"),
                alt.Tooltip(f"mean({measure_field})", title="Daily Average", format="0.1f"),
                alt.Tooltip(f"max({measure_field})", title="Maximum value"),
            ],
        )
    )
    chart_quantile = draw_quartiles(x=df_parking_spaces["date"], y=df_parking_spaces[measure_field])

    st.altair_chart(chart_parking_spaces + chart_quantile, use_container_width=True)

    pass


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
    if selected_time_granularity == TimeGranularity.week:
        tu_transform = "yearweek"
    elif selected_time_granularity == TimeGranularity.month:
        tu_transform = "yearmonth"
    else:
        tu_transform = "yearmonthdate"

    show_occupancy_timeline(df_room_usage, df_room_count, selected_hotel, tu_transform)
    show_number_of_guests(df_actions, df_booking, selected_hotel, tu_transform)
    show_parking_spaces_usage(df_booking, df_actions, selected_hotel, tu_transform)


if __name__ == "__main__":
    cols = st.columns(3)
    with cols[0]:
        selected_hotel = st.radio(label="hotel", options=list(Hotel), index=0, format_func=lambda h: h.value)

    with cols[1]:
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

    overview_tab, hotel_usage_tab = st.tabs(["Overview", "Hotel Usage"])

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
