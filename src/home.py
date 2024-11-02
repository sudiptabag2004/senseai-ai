import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

from email_validator import validate_email, EmailNotValidError
from menu import menu
from auth import login_or_signup_user, get_logged_in_user
from lib.init import init_app
from lib.db import (
    get_all_milestone_progress,
    get_all_verified_tasks,
    get_solved_tasks_for_user,
)
from components.streak import show_streak
from components.leaderboard import show_leaderboard
from components.milestone_learner_view import show_milestone_card

# init_auth_from_cookies()

init_app()


if "email" in st.query_params:
    login_or_signup_user(st.query_params["email"])

if "is_hv_learner" in st.query_params:
    st.session_state.is_hv_learner = int(st.query_params["is_hv_learner"])

if "view" in st.query_params:
    st.session_state.view = st.query_params["view"]
else:
    st.session_state.view = "milestone"

if "email" not in st.session_state:
    st.session_state.email = None

if "is_hv_learner" not in st.session_state:
    st.session_state.is_hv_learner = False


def clear_auth():
    st.query_params.clear()
    st.session_state.email = None
    st.rerun()


st.container(height=20, border=False)


def show_roadmap_as_list(tasks):
    st.write("Select a task by clicking beside the index of the task")

    df = pd.DataFrame(tasks)

    if not len(df):
        st.error(
            "No tasks added yet. Ask you mentors/teachers to add tasks for you to solve."
        )
        st.stop()

    df["status"] = df.apply(lambda x: "✅" if x["completed"] else "", axis=1)

    filtered_df = df[df["verified"]][["status", "id", "name", "description", "tags"]]

    if not len(filtered_df):
        st.error(
            "No tasks added yet. Ask you mentors/teachers to add tasks for you to solve."
        )
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
        df_actions.write("Do you want to work on this task?")
        task_id = filtered_df.iloc[event.selection["rows"][0]]["id"]
        df_actions.link_button(
            "Yes", f"/task?id={task_id}&email={st.session_state.email}"
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


def update_view(all_tasks):
    st.query_params.view = "list" if st.session_state.show_list_view else "milestone"


def show_roadmap():
    all_tasks = get_all_verified_tasks()
    solved_task_ids = get_solved_tasks_for_user(st.session_state.email)
    for task in all_tasks:
        if task["id"] in solved_task_ids:
            task["completed"] = True
        else:
            task["completed"] = False

    st.toggle(
        "Show List View",
        key="show_list_view",
        value=st.session_state.view == "list",
        on_change=update_view,
        args=(all_tasks,),
    )

    if st.session_state.show_list_view:
        show_roadmap_as_list(all_tasks)
    else:
        show_roadmap_by_milestone(all_tasks)


logged_in_user = get_logged_in_user()


def login():
    global logged_in_user
    if not logged_in_user:
        logged_in = False

        placeholder = st.empty()

        with placeholder.form("login_form"):
            email = st.text_input("Email")

            if st.form_submit_button("Login"):
                try:
                    # Check that the email address is valid. Turn on check_deliverability
                    # for first-time validations like on account creation pages (but not
                    # login pages).
                    emailinfo = validate_email(email, check_deliverability=True)

                    # After this point, use only the normalized form of the email address,
                    # especially before going to a database query.
                    login_or_signup_user(emailinfo.normalized)
                    st.query_params.email = st.session_state.email
                    # st.rerun()
                    logged_in = True
                    logged_in_user = get_logged_in_user()

                except EmailNotValidError as e:
                    # The exception message is human-readable explanation of why it's
                    # not a valid (or deliverable) email address.
                    st.error("Invalid email")

        if logged_in:
            placeholder.empty()
            login()

    else:
        cols = st.columns([4, 0.1, 3])
        with cols[0]:
            st.markdown(f"Welcome `{st.session_state.email}`! Let's begin learning! 🚀")
            # st.link_button(
            #     "👨‍💻👩‍💻 Start solving tasks",
            #     f"/task_list?email={st.session_state.email}",
            # )
            show_roadmap()

        with cols[-1]:
            show_streak()
            show_leaderboard()


login()

menu(logged_in_user)


def show_footer():
    st.sidebar.divider()

    st.sidebar.text("Built with ❤️ by HyperVerge Academy")

    if st.session_state.email:
        if st.sidebar.button("Logout"):
            clear_auth()


show_footer()

if not st.query_params:
    st.query_params.clear()
