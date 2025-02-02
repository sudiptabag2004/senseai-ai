from typing import Literal, TypeVar
import streamlit as st
from lib.db import get_streaks, get_user_streak, get_solved_tasks_for_user
from lib.config import leaderboard_view_types
from lib.profile import get_display_name_for_user
from models import LeaderboardViewType
from .base import set_box_style, show_box_header


def show_user_info(
    name,
    email,
    streak,
    tasks,
    rank,
    show_separator=False,
    highlight_user_row: bool = False,
):
    if show_separator:
        st.markdown('<div class="separator"></div>', unsafe_allow_html=True)

    is_logged_in_user = email == st.session_state.email

    col1, col2 = st.columns([1, 5])

    with col1:
        if rank is not None and rank <= 3:
            medal_image = open(f"lib/assets/leaderboard_{rank}.svg").read()
            st.markdown(
                f'<div style="display: flex; justify-content: center; align-items: center; height: 100%;">'
                f"{medal_image}"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            if st.session_state.theme["base"] == "dark":
                text_color = "white"
                border_style = "border: 1px solid white;"
                highlight_background_color = "#424bf5"
            else:
                text_color = "black"
                border_style = "border: 1px solid black;"
                highlight_background_color = "#b6d9e0"

            if rank is None:
                rank = "-"
                border_style = ""

            if highlight_user_row and is_logged_in_user:
                background_color_style = (
                    f"background-color: {highlight_background_color};"
                )
            else:
                background_color_style = ""

            st.markdown(
                f'<div style="display: flex; justify-content: center; align-items: center; height: 100%;">'
                f'<div style="width: 30px; height: 30px; border-radius: 50%; {border_style} {background_color_style} display: flex; justify-content: center; align-items: center;">'
                f'<span style="color: {text_color};">{rank}</span>'
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    with col2:
        user_text = " (You)" if is_logged_in_user else ""

        st.markdown(
            f'<p style="text-decoration: none; margin-bottom: 0;">{name}{user_text}</p>'
            f'<p style="margin-top: 0;">Streak: {streak} | Tasks Completed: {tasks}</p>',
            unsafe_allow_html=True,
        )


def get_leaderboard(view_type: LeaderboardViewType, cohort_id: int):
    if view_type not in leaderboard_view_types:
        raise ValueError(f"Invalid view type: {view_type}")

    streaks = get_streaks(view_type, cohort_id=cohort_id)

    users_data = []
    for streak_data in streaks:
        if not streak_data["count"]:
            continue

        solved_tasks = get_solved_tasks_for_user(
            streak_data["user"]["id"], cohort_id, view_type
        )
        tasks_completed = len(solved_tasks)
        users_data.append(
            (
                get_display_name_for_user(streak_data["user"]),
                streak_data["user"]["email"],
                streak_data["count"],
                tasks_completed,
            )
        )

    sorted_users = sorted(users_data, key=lambda x: (x[-2], x[-1]), reverse=True)

    top_performers = []
    other_performers = []
    previous_streak = None
    previous_tasks_completed = None
    rank = 0

    for name, email, streak_count, tasks_completed in sorted_users:
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
            other_performers.append((name, email, streak_count, tasks_completed, rank))
            continue

        top_performers.append((name, email, streak_count, tasks_completed, rank))

    return top_performers, other_performers


def _show_leaderboard(cohort_id: int, view_type: Literal["top", "full"] = "top"):

    tabs = st.tabs(leaderboard_view_types)

    container_kwargs = {}

    if view_type == "full":
        container_kwargs = {
            "height": 500,
            "border": False,
        }

    for tab_index, tab in enumerate(tabs):
        with tab:
            with st.container(**container_kwargs):
                top_performers, other_performers = get_leaderboard(
                    leaderboard_view_types[tab_index], cohort_id
                )
                is_logged_in_user_performer = False

                performers_to_show = (
                    top_performers
                    if view_type == "top"
                    else top_performers + other_performers
                )

                for index, (
                    name,
                    email,
                    streak_count,
                    tasks_completed,
                    rank,
                ) in enumerate(performers_to_show):
                    show_user_info(
                        name,
                        email,
                        streak_count,
                        tasks_completed,
                        rank,
                        show_separator=index != 0,
                        highlight_user_row=view_type == "full",
                    )
                    if st.session_state.email == email:
                        is_logged_in_user_performer = True

                if not is_logged_in_user_performer:
                    logged_in_user_info = [
                        info
                        for info in other_performers
                        if info[1] == st.session_state.email
                    ]

                    if not logged_in_user_info:
                        logged_in_user_info = (
                            get_display_name_for_user(st.session_state.user),
                            st.session_state.user["email"],
                            0,
                            len(
                                get_solved_tasks_for_user(
                                    st.session_state.user["id"],
                                    cohort_id,
                                    leaderboard_view_types[tab_index],
                                )
                            ),
                            None,
                        )
                    else:
                        logged_in_user_info = logged_in_user_info[0]

                    show_separator = len(top_performers) > 0

                    show_user_info(
                        logged_in_user_info[0],
                        logged_in_user_info[1],
                        logged_in_user_info[2],
                        logged_in_user_info[3],
                        logged_in_user_info[4],
                        show_separator=show_separator,
                        highlight_user_row=view_type == "full",
                    )


@st.dialog("Leaderboard")
def show_full_leaderboard_dialog(cohort_id: int):
    _show_leaderboard(cohort_id=cohort_id, view_type="full")


def show_leaderboard(cohort_id: int):
    set_box_style()

    with st.container(border=True):
        show_box_header("Top Performers")
        _show_leaderboard(cohort_id=cohort_id, view_type="top")

    st.button(
        "Show Full Leaderboard",
        type="primary",
        use_container_width=True,
        on_click=show_full_leaderboard_dialog,
        args=(cohort_id,),
    )
