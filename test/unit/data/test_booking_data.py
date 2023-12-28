import datetime as dt

import pandera as pa

from hotels.load_data import load_booking_data


class ReservationSchema(pa.DataFrameModel):
    reservation_id: str = pa.Field(nullable=False)
    arrival_date: dt.datetime = pa.Field(nullable=False)
    adr: float = pa.Field(nullable=False)
    adults: int = pa.Field(nullable=False)
    children: int = pa.Field(nullable=False)
    babies: int = pa.Field(nullable=False)
    n_lodgers: int = pa.Field(nullable=False, ge=0)


def test_booking_data():
    df = load_booking_data()

    try:
        ReservationSchema.validate(df, lazy=True)
    except pa.errors.SchemaErrors as e:
        print(e.failure_cases)
        raise e
