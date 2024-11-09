import streamlit as st
import pandas as pd
from lib.db import (
    get_all_milestone_progress,
    get_all_verified_tasks,
    get_solved_tasks_for_user,
)
from components.milestone_learner_view import show_milestone_card


def show_roadmap_as_list(tasks, is_review_mode: bool = False, learner_email: str = None):
    st.write("Select a task by clicking beside the `id` of the task")

    df = pd.DataFrame(tasks)

    if is_review_mode:
        empty_error_message = "No tasks added yet."
    else:
        empty_error_message = "No tasks added yet. Ask your mentors/teachers to add tasks for you to solve."

    if not len(df):
        st.error(empty_error_message)
        st.stop()

    df["status"] = df.apply(lambda x: "✅" if x["completed"] else "", axis=1)

    filtered_df = df[df["verified"]][["status", "id", "name", "description", "tags"]]

    if not len(filtered_df):
        st.error(empty_error_message)
        st.stop()

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
        link = f"/task?id={task_id}&email={st.session_state.email}"

        if is_review_mode:
            link += f"&learner={learner_email}&mode=review"

        df_actions.link_button(
            "Yes",
            link,
        )
        # print()
        # delete_tasks(event.selection['rows'])


def show_roadmap_by_milestone(all_tasks):
    all_milestone_data = get_all_milestone_progress(st.session_state.email)
    for milestone_data in all_milestone_data:
        milestone_tasks = [
            task
            for task in all_tasks
            if task["milestone_id"] == milestone_data["milestone_id"]
        ]

        milestone_tasks = sorted(milestone_tasks, key=lambda x: x["completed"])

        show_milestone_card(
            {
                "id": milestone_data["milestone_id"],
                "name": milestone_data["milestone_name"],
                "color": milestone_data["milestone_color"],
            },
            milestone_data["completed_tasks"],
            milestone_data["total_tasks"],
            milestone_tasks,
        )


def update_task_view():
    st.query_params.view = "list" if st.session_state.show_list_view else "milestone"


def get_tasks_with_completion_status(user_email: str, milestone_id: int = None):
    all_tasks = get_all_verified_tasks(milestone_id)
    solved_task_ids = get_solved_tasks_for_user(user_email)

    for task in all_tasks:
        if task["id"] in solved_task_ids:
            task["completed"] = True
        else:
            task["completed"] = False

    return all_tasks


def show_roadmap():
    all_tasks = get_tasks_with_completion_status(st.session_state.email)

    st.toggle(
        "Show List View",
        key="show_list_view",
        value=st.session_state.view == "list",
        on_change=update_task_view,
    )

    if st.session_state.show_list_view:
        show_roadmap_as_list(all_tasks)
    else:
        show_roadmap_by_milestone(all_tasks)
