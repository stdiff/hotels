import os

import streamlit as st

from hotels import PROJ_ROOT

os.environ["AWS_ACCESS_KEY_ID"] = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]
readme_path = PROJ_ROOT / "README.md"


if __name__ == "__main__":
    with readme_path.open() as fo:
        st.markdown("".join(fo.readlines()))
