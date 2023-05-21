import datetime as dt

import pandas as pd
import tomli
from sqlalchemy import create_engine

from hotels import PROJ_ROOT
from hotels.data import DataLoader


class DataLoaderSnowflake(DataLoader):
    secrets_path = PROJ_ROOT / ".streamlit" / "secrets.toml"
    dwh_name = "tiny_warehouse_mg"
    database_name = "stats"
    schema_name = "hotel"
    table_name = "reservations"
    credentials = tomli.load(secrets_path.open("rb"))["snowflake"]

    def get_sql_alchemy_engine(self):
        conn_str = "snowflake://{user}:{password}@{account}/{database}/{schema}".format(
            database=self.database_name, schema=self.schema_name, **self.credentials
        )
        return create_engine(conn_str)

    def check_connection_to_snowflake(self):
        engine = self.get_sql_alchemy_engine()
        connection = engine.connect()
        try:
            results = connection.execute("SELECT current_version()")
            if results:
                print("The connection to Snowflake was successful.")
        except Exception as e:
            print("Something wrong.")
            raise e
        finally:
            connection.close()
            engine.dispose()

    def load_raw_data(self) -> pd.DataFrame:
        sql = """select * from reservations"""
        engine = self.get_sql_alchemy_engine()
        return pd.read_sql(sql, engine)


    def get_min_date(self) -> dt.date:
        sql = """
        select min(to_date(concat(arrival_date_day_of_month, '/', arrival_date_month, '/', arrival_date_year), 'DD/MMMM/YYYY')) as min_date
          from reservations
        """
        engine = self.get_sql_alchemy_engine()
        conn = engine.connect()
        try:
            conn.execute(f"USE SCHEMA {self.schema_name}")
            results = conn.execute(sql).fetchone()
            return results[0]
        except Exception as e:
            raise e
        finally:
            conn.close()
            engine.dispose()

    def get_max_date(self) -> dt.date:
        sql = """
        select max(to_date(concat(arrival_date_day_of_month, '/', arrival_date_month, '/', arrival_date_year), 'DD/MMMM/YYYY')) as max_date
          from reservations
        """
        engine = self.get_sql_alchemy_engine()
        conn = engine.connect()
        try:
            conn.execute(f"USE SCHEMA {self.schema_name}")
            results = conn.execute(sql).fetchone()
            return results[0]
        except Exception as e:
            raise e
        finally:
            conn.close()
            engine.dispose()

