import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from lib.user import get_user_activity_for_year
from datetime import datetime, timedelta
import seaborn as sns


# Create the heatmap
def plot_activity_heatmap(data, fontsize=6):
    # Prepare the data
    data["weekday"] = data["date"].dt.weekday
    data["week"] = data["date"].dt.isocalendar().week

    # Use pivot_table with weeks
    pivot_data = data.pivot_table(
        index="weekday", columns="week", values="count", aggfunc="sum"
    )

    fig, ax = plt.subplots(figsize=(16, 3))

    # Create the heatmap
    sns.heatmap(
        pivot_data,
        cmap="Greens",
        square=True,
        linewidths=1,
        linecolor="white",
        cbar=False,
        xticklabels=[],
        ax=ax,
    )

    # Customize y-axis with single-letter days (right-padded with spaces)
    ax.set_yticks(
        np.arange(7) + 0.5,
        ["M  ", "T  ", "W  ", "T  ", "F  ", "S  ", "S  "],
        rotation=0,
        fontsize=fontsize,
    )

    # Remove tick marks
    ax.tick_params(axis="both", which="both", length=0)

    # Add month labels at the bottom
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    # Calculate week positions for each month
    weeks_per_month = [4, 8, 13, 17, 22, 26, 30, 35, 39, 43, 48, 52]

    # Add month labels at the bottom with more space
    for i, month in enumerate(months):
        start_week = weeks_per_month[i - 1] if i > 0 else 0
        end_week = weeks_per_month[i]
        middle_point = start_week + (end_week - start_week) / 2
        ax.text(middle_point, 8.5, month, ha="center", va="bottom", fontsize=fontsize)

    ax.set_xlabel("")
    ax.set_ylabel("")

    # Adjust layout to prevent label cutoff and add more space at bottom
    plt.subplots_adjust(bottom=0.5)

    return fig


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

    # dates = date_range(f"{selected_year}-01-01", f"{selected_year}-12-31")

    start_date = datetime(selected_year, 1, 1)
    end_date = datetime(selected_year, 12, 31)
    days = (end_date - start_date).days + 1
    dates = [start_date + timedelta(days=x) for x in range(days)]

    activity = get_user_activity_for_year(st.session_state.user["id"], selected_year)

    data = pd.DataFrame({"date": dates, "count": activity})

    fig = plot_activity_heatmap(data)

    with cols[0]:
        st.pyplot(fig)
