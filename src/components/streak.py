from typing import List
import random
import streamlit as st
from datetime import datetime, timedelta
from lib.db import get_user_streak, get_user_activity_last_n_days
from .base import set_box_style, show_box_header


def display_day_level_streak(user_activity: List[datetime]):
    # Custom CSS for the boxes
    st.markdown(
        """
    <style>
        .day-box {
            width: 40px;
            height: 40px;
            border: 1px solid #ccc;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
            margin-top: -20px;
            margin-bottom: 20px;
        }
        .active {
            background-color: #ffd700;
            color: black;
        }
        .inactive {
            background-color: #f0f0f0;
            color: #888;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Function to create a day box
    def day_box(day, is_active):
        class_name = "active" if is_active else "inactive"
        return f'<div class="day-box {class_name}">{day}</div>'

    # Get the current date
    today = datetime.now().date()

    # Generate the list of day numbers with the current day at the center
    today_index = 3  # Index of today in the 7-day list (0-based)
    days = [(today - timedelta(days=today_index - i)).day for i in range(7)]

    # Create columns for each day
    cols = st.columns(7)

    active_days = [date.day for date in user_activity]

    # Display the boxes
    for i, day in enumerate(days):
        is_active = day in active_days
        cols[i].markdown(day_box(day, is_active), unsafe_allow_html=True)


def show_streak():
    user_streak = get_user_streak(st.session_state.email)
    # Get the user's activity for the last 3 days as we are displaying a week's activity
    # with the current day in the center
    user_week_activity = get_user_activity_last_n_days(st.session_state.email, 3)

    streak_count = len(user_streak)

    set_box_style()

    with st.container(border=True):
        energizing_emojis = ["🚀", "💪", "🔥", "⚡", "🌟", "🏆", "💯", "🎉"]
        streak_text = f"{streak_count} {'day' if streak_count == 1 else 'days'}"

        if streak_count > 0:
            streak_text = f" {random.choice(energizing_emojis)} " + streak_text

        show_box_header("Your Learning Streak")
        st.markdown(f"<strong>{streak_text}</strong>", unsafe_allow_html=True)

        display_day_level_streak(user_week_activity)
