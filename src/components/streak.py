from typing import List
import random
import streamlit as st
from datetime import datetime, timedelta
from lib.db import get_user_streak


def display_day_level_streak(user_streak: List[datetime]):
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

    # Find the most recent Sunday
    start_of_week = today - timedelta(days=today.weekday())

    # Generate the list of day numbers for the current week
    days = [(start_of_week + timedelta(days=i)).day for i in range(7)]

    # Create columns for each day
    cols = st.columns(7)

    active_days = [date.day for date in user_streak]

    # Display the boxes
    for i, day in enumerate(days):
        is_active = day in active_days
        cols[i].markdown(day_box(day, is_active), unsafe_allow_html=True)


def show_streak():
    user_streak = get_user_streak(st.session_state.email)
    streak_count = len(user_streak)
    cols = st.columns(2)

    with cols[0].container(border=True):
        energizing_emojis = ["🚀", "💪", "🔥", "⚡", "🌟", "🏆", "💯", "🎉"]
        streak_text = f"{streak_count} {'day' if streak_count == 1 else 'days'}"

        if streak_count > 0:
            streak_text = f" {random.choice(energizing_emojis)} " + streak_text

        st.markdown(f"**Your Learning Streak: {streak_text}**\n\n----------")

        display_day_level_streak(user_streak)
