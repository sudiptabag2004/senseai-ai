from typing import List, Optional, Dict, Literal
import pandas as pd
import streamlit as st


def get_containers():
    description_col = st.columns(1)[0]
    description_container = description_col.container(border=True)

    return description_container
