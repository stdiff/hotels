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

    return chart_bar + chart_quartiles


def draw_kpi_by_cat(
    data: pd.DataFrame,
    tu_transform: TUTransform,
    cat_field: str,
    kpi_field: str,
    *additional_kpis,
) -> alt.Chart:
    """

    :param data: DataFrame[date, cat_field, kpi_field, additional_kpi1, ...]
    :param tu_transform:
    :param cat_field: categorical variable
    :param kpi_field: numerical variable
    :param additional_kpis: values you want to show in the tooltip
    :return:
    """
    cats = sorted(data[cat_field].drop_duplicates())
    cats_selector = alt.selection_point(name=cat_field + "/" + kpi_field, fields=[cat_field], bind="legend")
    nearest = alt.selection_point(on="mouseover", nearest=True, empty=False, fields=["x", "y"])

    tooltip = [
        alt.Tooltip(cat_field),
        alt.Tooltip(f"{tu_transform}(date)"),
        alt.Tooltip(f"min(date)", title="Start date"),
        alt.Tooltip(f"max(date)", title="End date"),
        alt.Tooltip(f"mean({kpi_field})", format="0.2f", title=f"Avg {kpi_field} by day"),
    ]

    if additional_kpis:
        tooltip.extend(
            [alt.Tooltip(f"mean({kpi})", format="0.2f", title=f"Avg {kpi} by day") for kpi in additional_kpis]
        )

    chart_base: alt.Chart = (
        alt.Chart(data)
        .encode(
            x=f"{tu_transform}(date)",
            y=f"mean({kpi_field})",
            color=alt.Color(f"{cat_field}:N").scale(domain=cats),
            opacity=alt.condition(cats_selector, alt.value(1.0), alt.value(0.1)),
            tooltip=tooltip,
        )
        .add_params(cats_selector)
    )
    chart_lines = chart_base.mark_line()
    chart_layer = chart_base.mark_point().encode(opacity=alt.value(0)).add_params(nearest)
    return chart_lines + chart_layer
