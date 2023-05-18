from enum import Enum


class Hotel(str, Enum):
    city_hotel = "City Hotel"
    resort_hotel = "Resort Hotel"


class ReservationStatus(str, Enum):
    check_out = "Check-Out"
    canceled = "Canceled"
    no_show = "No-Show"
