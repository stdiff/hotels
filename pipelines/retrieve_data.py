"""
The purpose of this module is to provide functions to download the raw data
"""
import pandas as pd

from hotels.load_data import hotel_raw_data_path

DATA_URL = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/master/data/2020/2020-02-11/hotels.csv"


def download_raw_data():
    df = pd.read_csv(DATA_URL)
    df.to_parquet(hotel_raw_data_path)
    print(f"DOWNLOADED: {hotel_raw_data_path}")


def main():
    download_raw_data()


if __name__ == "__main__":
    main()
