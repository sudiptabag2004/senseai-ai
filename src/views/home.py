import streamlit as st
import numpy as np
from typing import Dict, List
import pandas as pd

from lib.db import (
    get_all_milestone_progress,
    get_user_cohorts,
    get_cohorts_for_org,
    get_user_cohort_groups,
    get_courses_for_cohort,
)

from components.streak import show_streak
from components.leaderboard import show_leaderboard
from lib.url import update_query_params
from auth import get_logged_in_user
from menu import menu
from views.roadmap import show_roadmap


def learner_view(selected_cohort: Dict):
    if "view" in st.query_params:
        st.session_state.view = st.query_params["view"]
    else:
        st.session_state.view = "milestone"

    cols = st.columns([4, 0.1, 3])
    with cols[0]:
        show_roadmap(selected_cohort["id"])

    with cols[-1]:
        show_streak(selected_cohort["id"])
        show_leaderboard(selected_cohort["id"])


@st.cache_data
def get_mentor_groups(user_id: int, cohort_id: int):
    return get_user_cohort_groups(user_id, cohort_id)


def mentor_view(selected_cohort: Dict):
    logged_in_user = get_logged_in_user()

    selected_group = None
    selected_learner = None

    if not selected_cohort:
        return

    mentor_groups = get_mentor_groups(logged_in_user["id"], selected_cohort["id"])

    cohort_courses = get_courses_for_cohort(selected_cohort["id"])

    cols = st.columns(3)

    with cols[0]:
        selected_course = st.selectbox(
            "Select a course",
            cohort_courses,
            format_func=lambda x: x["name"],
        )

    with cols[1]:
        selected_group = st.selectbox(
            "Select a group",
            mentor_groups,
            format_func=lambda x: x["name"],
            index=0,
        )

    with cols[2]:
        selected_learner = st.selectbox(
            "Select a learner",
            selected_group["learners"],
            format_func=lambda val: val["email"],
        )

    all_milestone_data = get_all_milestone_progress(
        selected_learner["id"], selected_course["id"]
    )
    rows = []

    for milestone_data in all_milestone_data:
        milestone_data["percent_completed"] = np.round(
            (milestone_data["completed_tasks"] / milestone_data["total_tasks"]) * 100,
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
            "total_tasks": st.column_config.NumberColumn("Total Tasks", width="small"),
            "% completed": st.column_config.NumberColumn("% Completed", width="small"),
        },
    )
    if not len(event.selection["rows"]):
        return

    df_actions.write("Do you want to dig deeper into this milestone?")
    milestone_id = df.iloc[event.selection["rows"][0]]["milestone_id"]
    df_actions.link_button(
        "Yes",
        f"/roadmap?milestone_id={milestone_id}&email={st.session_state.email}&learner={selected_learner['id']}&cohort={selected_cohort['id']}&course={selected_course['id']}&mode=review",
    )
    # print()
    # delete_tasks(event.selection['rows'])


def show_home():
    logged_in_user = get_logged_in_user()

    user_cohorts = get_user_cohorts(logged_in_user["id"])

    if "selected_org" not in st.session_state:
        st.session_state["selected_org"] = st.session_state.user_orgs[0]

    org_cohorts = get_cohorts_for_org(st.session_state["selected_org"]["id"])

    user_cohorts += org_cohorts

    is_mentor = False
    role = None

    if user_cohorts:
        cols = st.columns(2)
        with cols[0]:
            selected_cohort = st.selectbox(
                "Select a cohort",
                user_cohorts,
                format_func=lambda x: f"{x['name']} ({x['org_name']})",
                index=0,
            )

        if "role" in selected_cohort:
            role = selected_cohort["role"]
        else:
            role = "admin"

        if role == "mentor":
            cols[1].container(height=2, border=False)
            is_mentor = cols[1].toggle(
                "Switch to mentor view", key="is_mentor", value=True
            )
            st.divider()

        if is_mentor:
            mentor_view(selected_cohort)
        else:
            if role == "admin":
                st.info("You are seeing the learner view")

            learner_view(selected_cohort)
    else:
        st.info(
            "You are currently not a member of any cohort. Please ask your admin to add you to one!"
        )
        selected_cohort = None

    menu(logged_in_user, selected_cohort, role)
