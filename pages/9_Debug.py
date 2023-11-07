import altair as alt
import pandas as pd
import streamlit as st

from hotels.dashboard import set_page_config
from hotels.data_retrieval import load_raw_data
from hotels.data_processing import Preprocessor


def show_raw_data_tab(data: pd.DataFrame):
    st.header("Raw data")

    st.metric("Number of rows", len(data))

    cols = st.columns(4)
    hotel = cols.pop(0).radio("hotel", ["City Hotel", "Resort Hotel"], horizontal=True)
    arrival_date_year = cols.pop(0).selectbox("arrival_date_year", data["arrival_date_year"].unique().tolist())
    arrival_date_month = cols.pop(0).selectbox(
        "arrival_date_month",
        data.query("arrival_date_year == @arrival_date_year")["arrival_date_month"].unique().tolist(),
    )
    arrival_date_day_of_month = cols.pop(0).slider(
        "arrival_date_day_of_month",
        min_value=1,
        max_value=data.query("hotel == @hotel")
        .query("arrival_date_year == @arrival_date_year")
        .query("arrival_date_month == @arrival_date_month")["arrival_date_day_of_month"]
        .max(),
        value=1,
    )

    df_filtered = (
        data.query("hotel == @hotel")
        .query("arrival_date_year == @arrival_date_year")
        .query("arrival_date_month == @arrival_date_month")
        .query("arrival_date_day_of_month == @arrival_date_day_of_month")
    )

    st.metric("Number of rows", len(df_filtered))

    st.dataframe(df_filtered, use_container_width=True, hide_index=True)


def show_processed_data_tab(df_processed: pd.DataFrame):
    cols = st.columns(3)

    min_arrival_date = df_processed["arrival_date"].min()
    max_arrival_date = df_processed["arrival_date"].max()

    cols.pop(0).metric("Number of rows", len(df_processed))
    cols.pop(0).metric("Minimum Arrival date", f"{min_arrival_date:%Y-%m-%d}")
    cols.pop(0).metric("Maixmum Arrival date", f"{max_arrival_date:%Y-%m-%d}")

    df_tmp = df_processed.groupby("arrival_date").size().rename("row_count").reset_index()
    chart_base = alt.Chart(df_tmp).encode(x="arrival_date", y="row_count", tooltip=["arrival_date", "row_count"])
    chart_line = chart_base.mark_line(point=True, opacity=0.7)
    chart_point = chart_base.mark_line(strokeWidth=40, opacity=0.01)
    chart = (chart_line + chart_point).interactive()
    st.altair_chart(chart, use_container_width=True)

    selected_arrival_date = st.date_input(
        "Arrival Date", value=min_arrival_date, min_value=min_arrival_date, max_value=max_arrival_date
    )

    st.dataframe(df_processed.query("arrival_date == @selected_arrival_date"), use_container_width=True)


def show_dashboard():
    st.title("Debugging Room")
    st.warning("This dashboard is only for developers.", icon="⚠️")

    raw_data_tab, processed_data_tab = st.tabs(["Raw data", "Processed Data"])

    df_raw = load_raw_data()
    with raw_data_tab:
        show_raw_data_tab(df_raw)

    df_processed = Preprocessor.apply_all(df_raw)
    with processed_data_tab:
        show_processed_data_tab(df_processed)


if __name__ == "__main__":
    set_page_config()
    show_dashboard()
