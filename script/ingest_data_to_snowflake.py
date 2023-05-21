from typing import Dict
import datetime as dt
import json

import pandas as pd
from sqlalchemy import create_engine
from snowflake.snowpark import Session
from snowflake.connector import connect
import tomli

from hotels import PROJ_ROOT, DATA_PATH

secrets_path = PROJ_ROOT / ".streamlit" / "secrets.toml"
dwh_name = "tiny_warehouse_mg"
database_name = "stats"
schema_name = "hotel"
table_name = "reservations"
ddl_sql_path = PROJ_ROOT / "script" / "create_table_reservation.sql"


def get_credentials() -> Dict[str, str]:
    return tomli.load(secrets_path.open("rb"))["snowflake"]


def check_connection_to_snowflake1():
    credentials = get_credentials()
    session = Session.builder.configs(credentials).create()
    table = session.table("PETS.PUBLIC.MYTABLE")
    df = table.limit(10).collect()
    print(df)


def check_connection_to_snowflake2():
    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()

    try:
        cursor.execute("SELECT current_version()")
        one_row = cursor.fetchone()
        print(one_row)
    except Exception as e:
        print(e)
    finally:
        cursor.close()
        ctx.close()


def create_warehouse():
    """
    Virtual warehouses contain the servers that are required for you to perform queries and DML operations with Snowflake.
    https://docs.snowflake.com/en/user-guide/warehouses-overview.html
    """
    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"CREATE WAREHOUSE IF NOT EXISTS {dwh_name}")
    finally:
        cursor.close()
        ctx.close()


def create_database():
    """
    Databases contain your schemas, which contain your database objects
    """
    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
    finally:
        cursor.close()
        ctx.close()


def create_schema():
    """
    Schemas are the grouping of your database objects. These include your tables, the data within them, and views.
    """
    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE DATABASE {database_name}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
    finally:
        cursor.close()
        ctx.close()


def create_table_reservations():
    with ddl_sql_path.open("r") as fo:
        sql = "".join(fo.readlines())

    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()
    try:
        cursor.execute(f"USE DATABASE {database_name}")
        cursor.execute(f"USE SCHEMA {schema_name}")
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(sql)
    finally:
        cursor.close()
        ctx.close()


def insert_rows_reservations():
    """
    PUT → COPY INTO is not working probably because of the file type.
    - Question. How about the placeholder for SQL?
    - Question. How to insert a dataframe into a table without generating SQL commands? → sqlalchemy?

    WARNING: This is extremely slow.
    """

    df = pd.read_parquet(DATA_PATH)
    rows_json = df.to_json(orient="records")
    rows = json.loads(rows_json)

    credentials = get_credentials()
    ctx = connect(**credentials)
    cursor = ctx.cursor()

    try:
        cursor.execute(f"USE DATABASE {database_name}")
        cursor.execute(f"USE SCHEMA {schema_name}")

        for row in rows:
            fields = ", ".join([k for k, v in row.items() if v is not None])
            values = ", ".join(
                [
                    f"'{v}'" if isinstance(v, str) else (f"{v}" if k == "adr" else f"{int(v)}")
                    for k, v in row.items()
                    if v is not None
                ]
            )
            sql = f"INSERT INTO {table_name} ({fields}) VALUES ({values})"
            cursor.execute(sql)
    finally:
        cursor.close()
        ctx.close()


def insert_rows_reservations_sqlalchemy():
    """
    SQL compilation error: maximum number of expressions in a list exceeded, expected at most 16,384
    → We have to divide the data set into chunks manually.

    If we use pandas.to_sql, then

    205.37507 seconds for 119390 items → 581.3 items/sec
    """
    credentials = get_credentials()
    credentials["database"] = database_name
    credentials["schema"] = schema_name

    df = pd.read_parquet(DATA_PATH)
    print(len(df), "rows")
    expected_velocity = 300  # /sec
    expected_time = len(df) / expected_velocity
    s_groups = pd.Series([x // 16_000 for x in range(len(df))])

    engine = create_engine("snowflake://{user}:{password}@{account}/{database}/{schema}".format(**credentials))

    t0 = dt.datetime.now()
    t_expected = t0 + dt.timedelta(seconds=expected_time)
    print("START:               ", t0.isoformat())
    print("Probably finishes at:", t_expected.isoformat())
    for group_idx, data in df.groupby(s_groups):
        data.to_sql(table_name, engine, if_exists="append", index=False)
    t1 = dt.datetime.now()
    print("END:                 ", t1.isoformat())

    delta_t = (t1 - t0).total_seconds()
    velocity = len(df) / delta_t
    print(f"{delta_t} seconds for {len(df)} items → {velocity:0.1f} items/sec")

    connection = engine.connect()
    try:
        results = connection.execute(f"select count(*) as n_rows from {table_name}").fetchone()
        print(results[0])
    finally:
        connection.close()
        engine.dispose()


if __name__ == "__main__":
    # check_connection_to_snowflake2() ## ('7.17.0',)
    # create_warehouse()
    # create_database()
    # create_schema()
    create_table_reservations()
    # insert_rows_reservations()
    insert_rows_reservations_sqlalchemy()
