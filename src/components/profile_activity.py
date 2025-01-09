import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import july
from july.utils import date_range
from lib.db import get_user_activity_for_year
from datetime import datetime


def show_github_style_activity():
    current_year = datetime.now().year

    current_month = datetime.now().month

    if current_month < 2:
        default_year_index = 1
    else:
        default_year_index = 0

    year_options = np.arange(2024, current_year + 1)[::-1]

    st.markdown(f"**Your Activity**")

    cols = st.columns([8, 2])

    with cols[1]:
        selected_year = st.selectbox(
            "Select a year", year_options, index=default_year_index
        )

    fig, ax = plt.subplots()

    dates = date_range(f"{selected_year}-01-01", f"{selected_year}-12-31")
    data = get_user_activity_for_year(st.session_state.user["id"], selected_year)

    # total_messages = sum(data)

    july.heatmap(
        dates,
        data,
        cmap="github",
        # month_grid=True,
        horizontal=True,
        # value_label=True,
        date_label=False,
        weekday_label=True,
        month_label=True,
        year_label=False,
        # colorbar=True,
        fontfamily="monospace",
        fontsize=4,
        # title="Your Activity",
        ax=ax,  ## <- Tell July to put the heatmap in that Axes
    )

    with cols[0]:
        st.pyplot(fig)
