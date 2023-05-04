from pathlib import Path

PROJ_ROOT = Path(__file__).parents[1]
DATA_DIR = PROJ_ROOT / "data"
DATA_PATH = DATA_DIR / "hotels.parquet"
DATA_URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv"
