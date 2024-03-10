import os

import pandas as pd
import streamlit as st
from dvc import api as dvc

from hotels import PROJ_ROOT

readme_path = PROJ_ROOT / "README.md"
os.environ["AWS_ACCESS_KEY_ID"] = st.secrets["aws"]["AWS_ACCESS_KEY_ID"]
os.environ["AWS_SECRET_ACCESS_KEY"] = st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"]


if __name__ == "__main__":
    with readme_path.open() as fo:
        st.markdown("\n".join(fo.readlines()))
