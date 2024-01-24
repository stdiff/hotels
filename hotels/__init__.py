import datetime as dt
from pathlib import Path

PROJ_ROOT = Path(__file__).parents[1]
DATA_DIR = PROJ_ROOT / "data"

data_start_date = dt.date(2015, 7, 1)
data_end_date_incl = dt.date(2017, 8, 31)
