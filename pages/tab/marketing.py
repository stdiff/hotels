import altair as alt
import pandas as pd
import streamlit as st

from hotels import data_start_date, data_end_date_incl
from hotels.dashboard import draw_daily_kpi_with_quoters, draw_kpi_by_cat
from hotels.models import Hotel, TimeGranularity, TUTransform


def draw_line_charts_top10(df_actions_ext: pd.DataFrame, tu_transform: TUTransform, cat_field: str, kpi_field: str):
    top10_cats = (
        df_actions_ext.groupby(cat_field, as_index=False)[kpi_field]
        .sum()
        .assign(rank=lambda x: x[kpi_field].rank(method="min", ascending=False))
        .sort_values(by="rank", ascending=True)
        .query("rank <= 10")[cat_field]
        .to_list()
    )

    df_kpi_by_cat: pd.DataFrame = (
        df_actions_ext.assign(country=lambda x: x[cat_field].apply(lambda c: c if c in top10_cats else "other"))
        .groupby(["date", cat_field])[kpi_field]
        .sum()
        .reset_index()
    )

    chart = draw_kpi_by_cat(df_kpi_by_cat, tu_transform, cat_field, kpi_field)
    st.altair_chart(chart, use_container_width=True)


def show_marketing_tab(
    df_booking: pd.DataFrame,
    df_actions: pd.DataFrame,
    tu_transform: TUTransform,
):
    st.header("Marketing")

    cols = ["hotel", "reservation_id", "adults", "children", "babies", "n_lodgers", "sales", "country"]
    df_actions_ext = df_actions.merge(
        df_booking.assign(sales=lambda x: x["adr"] * x["n_nights"] / x["n_stay_actual"])[cols]
    ).query("action != 'departure'")

    st.subheader("Number of guests by country")
    kpi_field = "number of guests"
    draw_line_charts_top10(df_actions_ext.rename(columns={"n_lodgers": kpi_field}), tu_transform, "country", kpi_field)

    st.subheader("Sales by country")
    kpi_field = "sales"
    draw_line_charts_top10(df_actions_ext, tu_transform, "country", kpi_field)

    st.subheader("Number of reservations of families")
    df_count_family = (
        df_actions_ext.assign(is_family=lambda x: x["children"] + x["babies"] > 0)
        .groupby(["date", "is_family"])
        .size()
        .rename("n_reservations")
        .reset_index()
        .pivot_table(index="date", columns="is_family", values="n_reservations", aggfunc="sum", fill_value=0)
        .melt(var_name="is_family", value_name="number of reservations", ignore_index=False)
        .reset_index()
    )
    chart_family_count = draw_kpi_by_cat(df_count_family, tu_transform, "is_family", "number of reservations")
    st.altair_chart(chart_family_count, use_container_width=True)

    st.subheader("Marketing segments and distribution channels")

    st.markdown(
        """
    - [Marketing segment](https://www.coursera.org/articles/market-segmentation): 
      Segmentations of potential customers based on shared characteristics.
      - [Online TA](https://www.tripsavvy.com/best-online-travel-agencies-4776301): Online Travel Agency. e.g. Booking.com
      - [Offline TA/TO](https://www.getgoing.com/blog/online-travel-agency-vs-offline/#offlineagencies): Travel Agency with physical offices. 
    - [Distribution channel](https://www.cvent.com/en/blog/hospitality/hotel-distribution-channels):
      Various ways in which hotels can sell rooms to potential customers ([list](https://www.littlehotelier.com/channel-manager/booking-channels/)).
      - [GDS](https://www.siteminder.com/r/global-distribution-system/): Worldwide reservation system which connects travel agencies and hotels
    """
    )

    df_not_cancelled = df_booking.query("is_canceled == 0")

    df_segment_vs_channel = (
        pd.crosstab(df_not_cancelled["market_segment"], df_not_cancelled["distribution_channel"])
        .reset_index()
        .melt(id_vars="market_segment", value_name="count")
    )

    chart_base: alt.Chart = (
        alt.Chart(df_segment_vs_channel)
        .encode(
            x=alt.X("distribution_channel").axis(labelAngle=0, orient="top").title("Distribution Channel"),
            y=alt.Y("market_segment").title("Market Segment"),
            color="count",
        )
        .properties(height=360)
    )
    middle_value = int(df_segment_vs_channel["count"].max() / 2)
    chart_rect = chart_base.mark_rect()
    chart_text = chart_base.mark_text(size=16).encode(
        text="count", color=alt.condition(f"datum.count > {middle_value}", alt.value("white"), alt.value("black"))
    )
    st.altair_chart(chart_rect + chart_text, use_container_width=True)
