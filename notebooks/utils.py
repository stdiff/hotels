import pandas as pd
import altair as alt


def adhoc_theme():
    theme_dict = {
        "config": {
            "view": {"height": 400, "width": 800},
            "title": {"fontSize": 24, "fontWeight": "normal", "titleAlign": "center"},
            "axisLeft": {"labelFontSize": 14, "titleFontSize": 16},
            "axisRight": {"labelFontSize": 14, "titleFontSize": 16},
            "header": {"labelFontSize": 14, "titleFontSize": 16, "titleAlign": "left"},
            "axisBottom": {"labelFontSize": 14, "titleFontSize": 16},
            "legend": {"labelFontSize": 12, "titleFontSize": 14},
            "range": {"category": {"scheme": "category10"}},
        }
    }
    return theme_dict


def notebook_setup():
    pd.options.display.max_colwidth = None
    pd.options.display.max_columns = None
    alt.data_transformers.disable_max_rows()
    alt.themes.register("adhoc_theme", adhoc_theme)
    alt.themes.enable("adhoc_theme")
