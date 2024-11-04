import streamlit as st
from lib.db import get_streaks, get_user_streak, get_solved_tasks_for_user
from .base import set_box_style, show_box_header


def show_user_info(email, streak, tasks, rank, show_separator=False):
    if show_separator:
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([1, 5])

    with col1:
        medal_image = open(f"lib/assets/leaderboard_{rank}.svg").read()
        st.markdown(
            f'<div style="display: flex; justify-content: center; align-items: center; height: 100%;">'
            f"{medal_image}"
            f"</div>",
            unsafe_allow_html=True,
        )

    with col2:
        user_text = " (You)" if email == st.session_state.email else ""
        st.markdown(
            f'<p style="text-decoration: none; margin-bottom: 0;">{email}{user_text}</p>'
            f'<p style="margin-top: 0;">Streak: {streak} | Tasks Completed: {tasks}</p>',
            unsafe_allow_html=True,
        )


def show_leaderboard():
    streaks = get_streaks()
    user_email = st.session_state.email

    set_box_style()

    with st.container(border=True):
        show_box_header("Top Performers")

        users_data = []
        for email, streak_count in streaks.items():
            if not streak_count:
                continue
            solved_tasks = get_solved_tasks_for_user(email)
            tasks_completed = len(solved_tasks)
            users_data.append((email, streak_count, tasks_completed))

        sorted_users = sorted(users_data, key=lambda x: (x[1], x[2]), reverse=True)

        top_performers = set()
        previous_streak = None
        previous_tasks_completed = None
        rank = 0

        for email, streak_count, tasks_completed in sorted_users:
            if (
                previous_streak is None
                or tasks_completed is None
                or streak_count != previous_streak
                or tasks_completed != previous_tasks_completed
            ):
                rank += 1
                previous_streak = streak_count
                tasks_completed = tasks_completed

            if rank > 3:
                break

            show_separator = len(top_performers) > 0
            top_performers.add(email)
            show_user_info(email, streak_count, tasks_completed, rank, show_separator)

        if user_email not in top_performers:
            streak_count = len(get_user_streak(user_email)) or 0
            tasks_completed = len(get_solved_tasks_for_user(user_email)) or 0
            show_separator = len(top_performers) > 0
            show_user_info(
                user_email,
                streak_count,
                tasks_completed,
                rank=4,
                show_separator=show_separator,
            )
