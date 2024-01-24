import altair as alt
import pandas as pd
import streamlit as st

from hotels.models import TUTransform


def set_page_config():
    st.set_page_config(page_icon=":hotel:", layout="wide")


def draw_quartiles(x: pd.Series, y: pd.Series, text_format: str = "0.1f") -> alt.Chart:
    s_q = y.quantile(q=[0.25, 0.50, 0.75])
    chart_base = alt.Chart(s_q.to_frame().assign(x=x.min()))
    chart_vline = chart_base.mark_rule(color="black", strokeDash=[5, 5]).encode(y=s_q.name)
    chart_text = chart_base.mark_text(dy=-10, fontSize=14, align="left").encode(
        x="x", y=s_q.name, text=alt.Text(s_q.name, format=text_format)
    )
    return chart_vline + chart_text


def draw_daily_kpi_with_quoters(
    data: pd.DataFrame, tu_transform: TUTransform, kpi_is_proportion: bool = False
) -> alt.Chart:
    kpi = [c for c in data.columns.to_list() if c != "date"][0]
    q1, q2, q3 = data[kpi].quantile(q=[0.25, 0.50, 0.75])

    cols = st.columns(4)
    if kpi_is_proportion:
        cols[0].metric(f"avg. {kpi} by day", f"{data[kpi].mean():0.1%}")
    else:
        cols[0].metric(f"avg. {kpi} by day", f"{data[kpi].mean():0.2f}")

    for i, q in enumerate([q1, q2, q3], 1):
        if kpi_is_proportion:
            cols[i].metric(f"Q{i} {kpi} by day", f"{q:0.1%}")
        else:
            cols[i].metric(f"Q{i} {kpi} by day", f"{q:0.2f}")

    y_axis = alt.Y(f"mean({kpi})").title(f"average {kpi} by day")
    color = alt.Color(f"mean({kpi})").title(kpi).scale(scheme="spectral")

    if kpi_is_proportion:
        y_axis = y_axis.axis(format="%").scale(domainMin=0, domainMax=1)
        color = color.scale(scheme="spectral", domainMin=0, domainMax=1).legend(format="%")
        format = "0.1%"
    else:
        format = "0.2f"

    chart_base: alt.Chart = alt.Chart(data).encode(
        x=alt.X(f"{tu_transform}(date)").title("date"),
        y=y_axis,
        color=color,
        tooltip=[
            alt.Tooltip(f"{tu_transform}(date)", title="date"),
            alt.Tooltip(f"min(date)", title="Start date"),
            alt.Tooltip(f"max(date)", title="End date"),
            alt.Tooltip(f"mean({kpi})", title="Daily Average", format=format),
        ],
    )
    chart_bar = chart_base.mark_bar(opacity=0.8)

    chart_quartiles = draw_quartiles(data["date"], data[kpi], text_format=format)

    # chart_rule = alt.Chart(pd.DataFrame({"date": data["date"].min(), "y": [q1, q2, q3]})).mark_rule().encode(y="y")
    # chart_text = chart_rule.mark_text(align="left", dy=-12, size=14).encode(x="date", y="y", text="y")
    return chart_bar + chart_quartiles
