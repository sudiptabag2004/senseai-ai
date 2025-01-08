import streamlit as st
import numpy as np
from typing import Dict, List
import pandas as pd

from lib.db import (
    get_user_metrics_for_all_milestones,
    get_user_cohorts,
    get_cohorts_for_org,
    get_mentor_cohort_groups,
    get_courses_for_cohort,
)

from components.streak import show_streak
from components.leaderboard import show_leaderboard
from lib.url import update_query_params
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


def mentor_view(selected_cohort: Dict):
    selected_group = None
    selected_learner = None

    if not selected_cohort:
        return

    mentor_groups = get_mentor_cohort_groups(
        st.session_state.user["id"], selected_cohort["id"]
    )

    cohort_courses = get_courses_for_cohort(selected_cohort["id"])

    cols = st.columns(3)

    with cols[0]:
        selected_course = st.selectbox(
            "Select a course",
            cohort_courses,
            format_func=lambda x: x["name"],
        )

    if not mentor_groups:
        st.info("You are not added to any group in this cohort")
        return

    with cols[1]:
        selected_group = st.selectbox(
            "Select a group",
            mentor_groups,
            format_func=lambda x: x["name"],
        )

    with cols[2]:
        selected_learner = st.selectbox(
            "Select a learner",
            selected_group["learners"],
            format_func=lambda val: val["email"],
        )

    all_milestone_data = get_user_metrics_for_all_milestones(
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
        f"/roadmap?milestone_id={milestone_id}&learner={selected_learner['id']}&cohort={selected_cohort['id']}&course={selected_course['id']}&mode=review",
    )
    # print()
    # delete_tasks(event.selection['rows'])


def show_home():
    user_cohorts = get_user_cohorts(st.session_state.user["id"])

    if "selected_org" not in st.session_state:
        st.session_state["selected_org"] = st.session_state.user_orgs[0]

    displayed_cohorts = get_cohorts_for_org(st.session_state["selected_org"]["id"])

    for cohort in displayed_cohorts:
        cohort["role"] = "admin"

    cohorts_added = set(cohort["id"] for cohort in displayed_cohorts)

    for cohort in user_cohorts:
        # to avoid showing the same cohort multiple times if the
        # admin is also added as a learner/mentor to the cohort
        if cohort["id"] in cohorts_added:
            continue

        displayed_cohorts.append(cohort)
        cohorts_added.add(cohort["id"])

    # to keep non-admin cohorts at the top
    displayed_cohorts = displayed_cohorts[::-1]

    is_mentor = False
    role = None

    if displayed_cohorts:

        def get_cohort_display_name(cohort):
            if "role" in cohort and cohort["role"] == "admin":
                return f"{cohort['name']} (by you)"
            else:
                return f"{cohort['name']} (by {cohort['org_name']})"

        cols = st.columns(2)
        with cols[0]:
            selected_cohort = st.selectbox(
                "Select a cohort",
                displayed_cohorts,
                format_func=get_cohort_display_name,
                index=0,
            )

        if "role" in selected_cohort:
            role = selected_cohort["role"]
        else:
            role = "admin"

        if role == "mentor":
            cols[1].container(height=2, border=False)
            is_mentor = cols[1].toggle("Mentor view", key="is_mentor", value=True)
            st.divider()

        if is_mentor:
            mentor_view(selected_cohort)
        else:
            if role == "admin":
                st.info(
                    "You are an admin for the cohort. You are seeing the learner view"
                )

            learner_view(selected_cohort)
    else:
        st.info(
            "You are currently not a member of any cohort. Please ask your admin to add you to one!"
        )
        selected_cohort = None

    menu(selected_cohort, role)
