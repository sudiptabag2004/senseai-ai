from typing import Dict
import streamlit as st
import pandas as pd
from typing import List, Dict
from lib.db import (
    get_user_metrics_for_all_milestones,
    get_all_verified_tasks_for_course,
    get_solved_tasks_for_user,
    get_courses_for_cohort,
)
from components.milestone_learner_view import show_milestone_card
from components.placeholder import show_empty_tasks_placeholder


def show_empty_error_message(role: str):
    if role == "admin":
        show_empty_tasks_placeholder()
    else:
        error_message = "No tasks added yet"
        st.error(error_message)


def show_roadmap_as_list(
    tasks,
    cohort_id: int,
    course_id: int,
    is_review_mode: bool = False,
    learner_id: int = None,
    role: str = None,
):
    df = pd.DataFrame(tasks)

    if not len(df):
        return show_empty_error_message(role)

    df["status"] = df.apply(lambda x: "✅" if x["completed"] else "", axis=1)

    df = df[df["verified"]][["status", "id", "name", "description", "tags"]]

    if not len(df):
        return show_empty_error_message(role)

    df["tags"] = df["tags"].apply(
        lambda tags: [tag["name"] for tag in tags] if tags else [],
    )

    st.write("Select a task by clicking beside the `id` of the task")

    df_actions = st.container(border=True)

    event = st.dataframe(
        df.style.map(
            lambda _: "background-color: #62B670;",
            subset=(df[df["status"] != ""].index, slice(None)),
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
        task_id = df.iloc[event.selection["rows"][0]]["id"]
        link = f"/task?id={task_id}&course={course_id}&cohort={cohort_id}"

        if is_review_mode:
            link += f"&learner={learner_id}&mode=review"

        df_actions.link_button(
            "Yes",
            link,
        )
        # print()
        # delete_tasks(event.selection['rows'])


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


def show_roadmap_by_milestone(
    all_tasks, user_id: int, cohort_id: int, course: Dict, role: str
):
    all_milestone_data = get_user_metrics_for_all_milestones(
        user_id, course_id=course["id"]
    )

    if not all_milestone_data:
        return show_empty_error_message(role)

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


def show_course_tab(course_tasks, cohort_id, course, user_id, role):
    if not course_tasks:
        return show_empty_error_message(role)

    if st.session_state.show_list_view:
        show_roadmap_as_list(course_tasks, cohort_id, course["id"], role)
    else:
        show_roadmap_by_milestone(course_tasks, user_id, cohort_id, course, role)


def show_roadmap_by_course(
    user_id: int, cohort_id: int, cohort_courses: List[Dict], role: str
):
    course_ids = [course["id"] for course in cohort_courses]

    default_course_id = int(st.query_params.get("course_id", course_ids[0]))
    course_id_to_course = {course["id"]: course for course in cohort_courses}

    def update_course_id_in_query_params():
        if st.session_state["selected_course_id"] is None:
            st.session_state["selected_course_id"] = int(st.query_params["course_id"])
            return

        st.query_params["course_id"] = str(st.session_state["selected_course_id"])

    st.session_state["selected_course_id"] = default_course_id
    selected_course_id = st.segmented_control(
        "Select course",
        course_ids,
        key="selected_course_id",
        format_func=lambda course_id: course_id_to_course[course_id]["name"],
        on_change=update_course_id_in_query_params,
    )

    course_tasks = get_tasks_with_completion_status(
        user_id, cohort_id, selected_course_id
    )
    show_course_tab(
        course_tasks, cohort_id, course_id_to_course[selected_course_id], user_id, role
    )


def update_task_view():
    st.query_params.view = "list" if st.session_state.show_list_view else "milestone"


def show_roadmap(cohort_id: int, cohort_courses: List[Dict], role: str):
    # st.toggle(
    #     "Show List View",
    #     key="show_list_view",
    #     value=st.session_state.view == "list",
    #     on_change=update_task_view,
    # )
    st.session_state.show_list_view = False

    show_roadmap_by_course(
        user_id=st.session_state.user["id"],
        cohort_id=cohort_id,
        cohort_courses=cohort_courses,
        role=role,
    )
