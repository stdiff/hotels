import pandas as pd

from hotels import DATA_PATH, DATA_URL

def download_data():
    df = pd.read_csv(DATA_URL)
    df.to_parquet(DATA_PATH)
    print(f"DOWNLOADED: {DATA_PATH}")


if __name__ == "__main__":
    download_data()