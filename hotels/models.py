from enum import Enum


class Hotel(str, Enum):
    city_hotel = "City Hotel"
    resort_hotel = "Resort Hotel"


class ReservationStatus(str, Enum):
    check_out = "Check-Out"
    canceled = "Canceled"
    no_show = "No-Show"


class TimeGranularity(str, Enum):
    day = "Day"
    week = "Week"
    month = "Month"


class TUTransform(str, Enum):
    yearweek = "yearweek"
    yearmonth = "yearmonth"
    yearmonthdate = "yearmonthdate"

    @classmethod
    def from_time_granularity(cls, time_granularity: TimeGranularity) -> "TUTransform":
        if not isinstance(time_granularity, TimeGranularity):
            raise ValueError(f"{time_granularity} does not belong to TimeGranularity")
        elif time_granularity == TimeGranularity.week:
            return TUTransform.yearweek
        elif time_granularity == TimeGranularity.month:
            return TUTransform.yearmonth
        elif time_granularity == TimeGranularity.day:
            return TUTransform.yearmonthdate
        else:
            raise ValueError("🤔")
