import streamlit as st

from hotels import PROJ_ROOT

readme_path = PROJ_ROOT / "README.md"

if __name__ == "__main__":
    with readme_path.open() as fo:
        st.markdown("\n".join(fo.readlines()))
