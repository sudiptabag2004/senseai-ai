import streamlit as st
import numpy as np
from typing import Dict, List
import pandas as pd

from lib.db import (
    get_all_milestone_progress,
    get_user_cohorts,
    get_cohort_group_learners,
)

from components.streak import show_streak
from components.leaderboard import show_leaderboard
from lib.url import update_query_params
from auth import get_logged_in_user
from menu import menu
from views.roadmap import show_roadmap


def learner_view():
    if "view" in st.query_params:
        st.session_state.view = st.query_params["view"]
    else:
        st.session_state.view = "milestone"

    cols = st.columns([4, 0.1, 3])
    with cols[0]:
        show_roadmap()

    with cols[-1]:
        show_streak()
        show_leaderboard()


def mentor_view(mentor_cohorts: List[Dict]):
    cols = st.columns(3)

    selected_cohort = None
    selected_group = None
    selected_learner = None

    with cols[0]:
        selected_cohort = st.selectbox(
            "Select a cohort",
            mentor_cohorts,
            format_func=lambda x: x["name"],
            index=0,
        )

    if selected_cohort:
        with cols[1]:
            selected_group = st.selectbox(
                "Select a group",
                selected_cohort["groups"],
                format_func=lambda x: x["name"],
                index=0,
            )

        if selected_group:
            group_learners = get_cohort_group_learners(selected_group["id"])
            with cols[2]:
                selected_learner = st.selectbox(
                    "Select a learner",
                    group_learners,
                    format_func=lambda val: val["email"],
                    index=0,
                )

        if not selected_learner:
            return

        all_milestone_data = get_all_milestone_progress(selected_learner["id"])
        rows = []

        for milestone_data in all_milestone_data:
            milestone_data["percent_completed"] = np.round(
                (milestone_data["completed_tasks"] / milestone_data["total_tasks"])
                * 100,
                2,
            )
            rows.append(
                [
                    milestone_data["milestone_id"],
                    milestone_data["milestone_name"],
                    milestone_data["completed_tasks"],
                    milestone_data["total_tasks"],
                    milestone_data["percent_completed"],
                ]
            )

        df = pd.DataFrame(
            rows,
            columns=[
                "milestone_id",
                "milestone_name",
                "tasks_completed",
                "total_tasks",
                "% completed",
            ],
        )

        df_actions = st.container(border=True)

        event = st.dataframe(
            df,
            on_select="rerun",
            selection_mode="single-row",
            hide_index=True,
            use_container_width=True,
            column_config={
                "milestone_id": None,
                "milestone_name": st.column_config.TextColumn("Milestone"),
                "tasks_completed": st.column_config.NumberColumn(
                    "Tasks Completed", width="small"
                ),
                "total_tasks": st.column_config.NumberColumn(
                    "Total Tasks", width="small"
                ),
                "% completed": st.column_config.NumberColumn(
                    "% Completed", width="small"
                ),
            },
        )
        if not len(event.selection["rows"]):
            return

        df_actions.write("Do you want to dig deeper into this milestone?")
        milestone_id = df.iloc[event.selection["rows"][0]]["milestone_id"]
        df_actions.link_button(
            "Yes",
            f"/roadmap?milestone_id={milestone_id}&email={st.session_state.email}&learner={selected_learner['id']}&mode=review",
        )
        # print()
        # delete_tasks(event.selection['rows'])


def is_mentor_for_cohort(user_cohort_dict: Dict) -> bool:
    return (
        len(
            [group for group in user_cohort_dict["groups"] if group["role"] == "mentor"]
        )
        > 0
    )


def show_home():
    logged_in_user = get_logged_in_user()

    user_cohorts = get_user_cohorts(logged_in_user["id"])

    mentor_cohorts = [cohort for cohort in user_cohorts if is_mentor_for_cohort(cohort)]

    if "is_mentor" in st.query_params:
        st.session_state.is_mentor = int(st.query_params["is_mentor"])

    if "is_mentor" not in st.query_params:
        st.session_state.is_mentor = False

    if st.session_state.is_mentor and not mentor_cohorts:
        st.error("You are not a mentor for any cohort")
        st.stop()

    if mentor_cohorts:
        st.toggle(
            "Switch to mentor view",
            key="is_mentor",
            on_change=update_query_params,
            args=("is_mentor", int),
        )

    if st.session_state.is_mentor:
        st.markdown("----")
        mentor_view(mentor_cohorts)
    else:
        if mentor_cohorts:
            st.info("You are currently seeing the learner view!")
            st.divider()

        learner_view()

    menu(logged_in_user, st.session_state.is_mentor)
