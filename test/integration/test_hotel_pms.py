from streamlit.testing.v1.app_test import AppTest


def test_hotel_pms_dashboard():
    at = AppTest.from_file("pages/1_Hotel_PMS.py", default_timeout=5)
    at.run()
    assert len(at.exception) == 0
