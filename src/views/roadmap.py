from typing import Dict
import streamlit as st
import pandas as pd
from lib.db import (
    get_all_milestone_progress,
    get_all_verified_tasks_for_course,
    get_solved_tasks_for_user,
    get_courses_for_cohort,
    get_tasks_for_course,
)
from components.milestone_learner_view import show_milestone_card
from auth import get_logged_in_user


def show_empty_error_message(is_review_mode: bool = False):
    if is_review_mode:
        error_message = "No tasks added yet!"
    else:
        error_message = "No tasks added yet. Ask your admin to add tasks!"

    st.error(error_message)


def show_roadmap_as_list(
    tasks,
    cohort_id: int,
    course_id: int,
    is_review_mode: bool = False,
    learner_id: int = None,
):
    df = pd.DataFrame(tasks)

    if not len(df):
        return show_empty_error_message(is_review_mode)

    df["status"] = df.apply(lambda x: "✅" if x["completed"] else "", axis=1)

    filtered_df = df[df["verified"]][["status", "id", "name", "description", "tags"]]

    if not len(filtered_df):
        return show_empty_error_message(is_review_mode)

    st.write("Select a task by clicking beside the `id` of the task")

    df_actions = st.container(border=True)

    event = st.dataframe(
        filtered_df.style.map(
            lambda _: "background-color: #62B670;",
            subset=(filtered_df[filtered_df["status"] != ""].index, slice(None)),
        ),
        on_select="rerun",
        selection_mode="single-row",
        use_container_width=True,
        hide_index=True,
        column_order=["id", "status", "tags", "name", "description"],
        column_config={
            # 'description': st.column_config.TextColumn(
            #     width='large',
            #     help='Description of the task'
            # ),
            # 'id': None
        },
    )

    if len(event.selection["rows"]):
        if is_review_mode:
            confirmation_message = "Do you want to review this task?"
        else:
            confirmation_message = "Do you want to work on this task?"

        df_actions.write(confirmation_message)
        task_id = filtered_df.iloc[event.selection["rows"][0]]["id"]
        link = f"/task?id={task_id}&email={st.session_state.email}&course={course_id}&cohort={cohort_id}"

        if is_review_mode:
            link += f"&learner={learner_id}&mode=review"

        df_actions.link_button(
            "Yes",
            link,
        )
        # print()
        # delete_tasks(event.selection['rows'])


def show_roadmap_for_course(all_tasks, user_id: int, cohort_id: int, course: Dict):
    all_milestone_data = get_all_milestone_progress(user_id, course_id=course["id"])

    if not all_milestone_data:
        return show_empty_error_message()

    for milestone_data in all_milestone_data:
        milestone_tasks = [
            task
            for task in all_tasks
            if task["milestone_id"] == milestone_data["milestone_id"]
        ]

        # milestone_tasks = sorted(milestone_tasks, key=lambda task: task["completed"])

        show_milestone_card(
            {
                "id": milestone_data["milestone_id"],
                "name": milestone_data["milestone_name"],
                "color": milestone_data["milestone_color"],
            },
            milestone_data["completed_tasks"],
            milestone_data["total_tasks"],
            milestone_tasks,
            cohort_id,
            course["id"],
        )


def show_roadmap_by_course(user_id: int, cohort_id: int):
    cohort_courses = get_courses_for_cohort(cohort_id)

    tabs = st.tabs([course["name"] for course in cohort_courses])

    for tab, course in zip(tabs, cohort_courses):
        course_tasks = get_tasks_with_completion_status(
            user_id, cohort_id, course["id"]
        )

        with tab:
            if not course_tasks:
                return show_empty_error_message()

            if st.session_state.show_list_view:
                show_roadmap_as_list(course_tasks, cohort_id, course["id"])
            else:
                show_roadmap_for_course(course_tasks, user_id, cohort_id, course)


def update_task_view():
    st.query_params.view = "list" if st.session_state.show_list_view else "milestone"


def get_tasks_with_completion_status(
    user_id: int, cohort_id: int, course_id: int, milestone_id: int = None
):
    all_tasks = get_all_verified_tasks_for_course(course_id, milestone_id)
    solved_task_ids = get_solved_tasks_for_user(user_id, cohort_id)

    for task in all_tasks:
        if task["id"] in solved_task_ids:
            task["completed"] = True
        else:
            task["completed"] = False

    return all_tasks


def show_roadmap(cohort_id: int):
    logged_in_user = get_logged_in_user()

    st.toggle(
        "Show List View",
        key="show_list_view",
        value=st.session_state.view == "list",
        on_change=update_task_view,
    )

    show_roadmap_by_course(user_id=logged_in_user["id"], cohort_id=cohort_id)
