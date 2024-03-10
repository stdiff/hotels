from typing import Literal
import datetime as dt

import altair as alt
import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import set_page_config
from hotels.load_data import load_booking_data
from hotels.models import Hotel, ReservationStatus

set_page_config()

_flow_type2flow_name = {"arrival": "Arrivals", "in-house": "in House (Occupied)", "departure": "Departures"}
FlowType = Literal["arrival", "in-house", "departure", "non-related"]


@st.cache_data(ttl="1h")
def load_data() -> pd.DataFrame:
    return load_booking_data()


def infobox_guest_flow(flow_name: str, n_rooms: int = 0, n_adults: int = 0, n_children: int = 0, n_babies: int = 0):
    n_guests = n_adults + n_children + n_babies
    st.subheader(flow_name)

    cols2 = st.columns(2)
    cols2.pop(0).metric("Rooms", n_rooms)
    cols2.pop(0).metric("Guests", n_guests)

    cols3 = st.columns(3)
    cols3.pop(0).metric("👤 Adults", n_adults)
    cols3.pop(0).metric("🧒 Children", n_children)
    cols3.pop(0).metric("👶 Babies", n_babies)


def find_flow_type(row: pd.Series, selected_date: dt.date) -> FlowType:
    # return:arrival, in_house, departure
    arrival_date = row["arrival_date"]
    actual_departure_date = row["actual_departure_date"]
    reservation_status = row["reservation_status"]
    reservation_status_date = row["reservation_status_date"]

    if arrival_date == selected_date and reservation_status_date >= selected_date:
        # Regardless the reservation status, the guests checked in if reservation status is updated after the arrival date.
        return "arrival"

    elif reservation_status == ReservationStatus.check_out and arrival_date < selected_date < actual_departure_date:
        return "in-house"

    elif reservation_status == ReservationStatus.check_out and selected_date == actual_departure_date:
        return "departure"

    else:
        return "non-related"


def show_meals_needed(df: pd.DataFrame):
    """
    :param df: DataFrame[flow_type, breakfast, lunch, dinner, n_lodgers]
    """
    st.subheader("Meals needed")

    def count_meals(data: pd.DataFrame, field: str) -> int:
        return (data[field] * data["n_lodgers"]).sum()

    n_breakfast = count_meals(df.query("flow_type in ('in-house', 'departure')"), "breakfast")
    n_lunch = count_meals(df.query("flow_type == 'in-house'"), "lunch")
    n_dinner = count_meals(df.query("flow_type in ('arrival', 'in-house')"), "dinner")

    st.metric("🍳 Breakfast", n_breakfast)
    st.metric("🍱 Lunch", n_lunch)
    st.metric("🍽️ Dinner", n_dinner)


def show_room_usage(df: pd.DataFrame):
    """
    :param df: DataFrame[flow_type, reserved_room_type, assigned_room_type]
    """
    st.subheader("Room usage")

    flow_types = ["arrival", "in-house", "departure"]
    room_types = sorted(set(df["reserved_room_type"].to_list() + df["assigned_room_type"].to_list()))

    chart_base = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("count()").title("number of rooms"),
            color=alt.Color("flow_type").scale(domain=flow_types),
        )
    )  # type: alt.Chart

    chart_from_yesterday = (
        chart_base.transform_filter("datum.flow_type != 'arrival'")
        .encode(
            y=alt.Y("assigned_room_type").title("Room type").scale(domain=room_types),
            color=alt.Color("flow_type").scale(domain=flow_types).legend(None),
        )
        .properties(title="Used by staying guests")
    )

    chart_new = (
        chart_base.transform_filter("datum.flow_type == 'arrival'")
        .encode(y=alt.Y("reserved_room_type").title("Room type").scale(domain=room_types))
        .properties(title="Will be used by new guests")
    )

    cols = st.columns(2)
    cols[0].altair_chart(chart_from_yesterday, use_container_width=True)
    cols[1].altair_chart(chart_new, use_container_width=True)


def show_morning_tab(df_selected_date: pd.DataFrame):
    st.header("☀️ Good Morning!")

    cols = st.columns(len(_flow_type2flow_name))
    for i, (flow_type, flow_name) in enumerate(_flow_type2flow_name.items()):
        with cols[i].container(border=True):
            df = df_selected_date.query("flow_type == @flow_type")

            infobox_guest_flow(
                flow_name,
                n_rooms=len(df),
                n_adults=df["adults"].sum(),
                n_children=df["children"].sum(),
                n_babies=df["babies"].sum(),
            )

    cols = st.columns([1, 4])
    with cols[0].container(border=True):
        show_meals_needed(df_selected_date)

    with cols[1].container(border=True):
        show_room_usage(df_selected_date)


def show_evening_tab(selected_hotel: Hotel, selected_date: dt.date, df_selected_date: pd.DataFrame):
    st.header("🌙 Good Evening!")

    def flow_type_evening(r: pd.Series) -> FlowType:
        flow_type: FlowType = r["flow_type"]

        if flow_type == "arrival" and r["reservation_status"] == ReservationStatus.check_out:
            if r["reservation_status_date"] == selected_date:
                return "non-related"
            else:
                return "in-house"
        elif flow_type == "departure":
            return "non-related"
        else:
            return flow_type

    df_evening = df_selected_date.assign(
        flow_type_morning=df_selected_date["flow_type"], flow_type=df_selected_date.apply(flow_type_evening, axis=1)
    )
    df_evening.query("flow_type != 'non-related'", inplace=True)

    cols = st.columns(3)
    for i, (flow_type, flow_name) in enumerate(_flow_type2flow_name.items()):
        with cols[i].container(border=True):
            df = df_evening.query("flow_type == @flow_type")
            infobox_guest_flow(
                flow_name,
                n_rooms=len(df),
                n_adults=df["adults"].sum(),
                n_children=df["children"].sum(),
                n_babies=df["babies"].sum(),
            )

    cols = st.columns([1, 4])
    with cols[0].container(border=True):
        show_meals_needed(df_selected_date)

    with cols[1].container(border=True):
        show_room_usage(df_evening)


if __name__ == "__main__":
    st.title("📖 Hotel PMS Dashboard")
    df_booking = load_data()

    with st.sidebar:
        st.subheader("Hotel")
        selected_hotel = st.radio(
            label="hotel", options=list(Hotel), index=0, format_func=lambda h: h.value, label_visibility="collapsed"
        )

        today = dt.date.today().replace(year=2016)
        selected_date = pd.to_datetime(
            st.date_input(
                label="date", value=today, min_value=data_start_date, max_value=data_end_date_incl, format="YYYY-MM-DD"
            )
        )
        st.info(f"Any date between {data_start_date} and {data_end_date_incl}")

    df_selected_date = df_booking.query("hotel == @selected_hotel").drop(columns=["hotel"], inplace=False)
    df_selected_date["flow_type"] = df_selected_date.apply(find_flow_type, selected_date=selected_date, axis=1)
    df_selected_date.query("flow_type != 'non-related'", inplace=True)

    morning_tab, evening_tab, readme_tab = st.tabs(["☀️ Morning", "🌙 Evening", "👀 README"])

    with morning_tab:
        show_morning_tab(df_selected_date)

    with evening_tab:
        show_evening_tab(selected_hotel, selected_date, df_selected_date)

    with readme_tab:
        st.markdown(
            """
        ## About this dashboard
        
        A (hotel) PMS (property management system) is a system managing the information about reservations of hotel 
        rooms. This dashboard provides something like a portal of a hotel PMS. Because the original data is not 
        historized, it is impossible to reproduce the data for an arbitrary time. This is the reason why this dashboard
        is "pseudo".
        
        ### Conclusions of non-historized data 
        
        We can not follow any change of reservations.
         
        - There are reservations whose actual departure dates are earlier than the reservation information. 
          Such a change probably happens at some point during their stay at the hotel, but the data shows only the date 
          when the guests leave the hotel. 
        
        ### Terms 
        
        - Arrivals: guests who arrive on the day
        - in House (Occupied): guests who checked in and will stay this night
        - Departures: guests who leave the hotel on the day
        - Meals needed: number of meals the hotel needs to prepare for guests
        - Room usage: number of rooms which are (will be) used by guests
        
        ### ☀️ Morning Tab
        
        The state of the dashboard if you open the dashboard at the very beginning of the day: 
        No guests arrived and no guest left. You can check the number of new guests and the number of guests who leave
        the hotel.  
        
        ### 🌙 Evening Tab
        
        The state of the dashboard if you open the dashboard at the end of the day: all new guests arrived and ones who 
        have to leave left. If you still see a positive number in Arrival section, they are "No-Show".
        
        ### References
        
        - [What is a Hotel Property Management System (PMS)?](https://www.oracle.com/hospitality/what-is-hotel-pms/)
        - [A list of examples of PMS](https://hoteltechreport.com/operations/property-management-systems)
        """
        )
