from streamlit.testing.v1.app_test import AppTest


def test_hotel_pms_dashboard():
    at = AppTest.from_file("pages/2_Internal_Dashboards.py", default_timeout=15)
    at.run()
    assert len(at.exception) == 0
