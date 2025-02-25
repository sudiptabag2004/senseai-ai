import streamlit as st

st.set_page_config(page_title="Profile | SensAI", layout="wide")

from typing import Dict, Literal

from lib.init import init_app

init_app()

from lib.user import get_user_by_id, update_user as update_user_in_db
from lib.profile import get_user_name, show_placeholder_icon
from lib.badge import get_all_badges_for_user
from components.badge import (
    show_badge,
    show_share_badge_prompt,
    show_download_badge_button,
)
from components.profile_activity import show_github_style_activity
from components.buttons import back_to_home_button
from auth import login_or_signup_user

login_or_signup_user()

back_to_home_button()

st.container(height=20, border=False)


def show_profile_icon(user: Dict):
    user_name = get_user_name(user)

    if user_name:
        display_name = user_name
    else:
        display_name = user["email"]

    show_placeholder_icon(display_name, user["default_dp_color"])


def profile_header(user: Dict):
    cols = st.columns([1, 5])

    with cols[0]:
        show_profile_icon(user)

    with cols[1]:
        user_name = get_user_name(user)
        if user_name:
            st.header(user_name)
        st.text(user["email"])


def refresh_user():
    st.session_state.user = get_user_by_id(st.session_state.user["id"])


def refresh_badges():
    st.session_state.badges = get_all_badges_for_user(st.session_state.user["id"])


refresh_user()

if "badges" not in st.session_state:
    refresh_badges()

if not st.session_state.user:
    st.error("User not found")
    st.stop()

profile_header(st.session_state.user)

st.container(height=20, border=False)

tab_names = [
    "Dashboard",
    "Badges",
    "Account",
]
tabs = st.tabs(tab_names)


with tabs[0]:
    show_github_style_activity()


def show_badges_tab():
    if not st.session_state.badges:
        st.info(
            "🚀 You haven't earned any badges yet. Solve tasks regularly to build streaks and complete milestones to earn badges."
        )
        return

    show_share_badge_prompt()

    num_cols = 4
    grid = st.columns(num_cols)
    for index, badge in enumerate(st.session_state.badges):
        with grid[index % num_cols]:
            badge_params = {
                "image_path": badge["image_path"],
                "bg_color": badge["bg_color"],
            }
            show_badge(
                badge["value"],
                badge["type"],
                "learner",
                badge_params,
                badge["cohort_name"],
                badge["org_name"],
                width=300,
                height=300,
            )
            show_download_badge_button(
                badge["value"],
                badge["type"],
                badge_params,
                badge["cohort_name"],
                badge["org_name"],
                key=badge["id"],
            )


with tabs[1]:
    show_badges_tab()


def update_account_details(
    first_name: str, middle_name: str, last_name: str, profile_color: str
):
    error_placeholder = st.empty()
    if not first_name:
        with error_placeholder:
            st.error("First name cannot be empty")
            return

    if not last_name:
        with error_placeholder:
            st.error("Last name cannot be empty")
            return

    error_placeholder.empty()

    update_user_in_db(
        st.session_state.user["id"], first_name, middle_name, last_name, profile_color
    )
    st.rerun()


def show_account_tab():
    with st.form("account_details", border=False):
        cols = st.columns(3)
        with cols[0]:
            first_name = st.text_input(
                "First Name*",
                key="first_name",
                value=st.session_state.user["first_name"],
            )

        with cols[1]:
            middle_name = st.text_input(
                "Middle Name",
                key="middle_name",
                value=st.session_state.user["middle_name"],
            )

        with cols[2]:
            last_name = st.text_input(
                "Last Name*", key="last_name", value=st.session_state.user["last_name"]
            )

        cols = st.columns(2)
        with cols[0]:
            email = st.text_input(
                "Email",
                value=st.session_state.email,
                disabled=True,
            )

        with cols[1]:
            profile_color = st.color_picker(
                "Profile Color",
                value=st.session_state.user["default_dp_color"],
                key="profile_color",
            )

        submit_button = st.form_submit_button(
            "Save",
            type="primary",
        )
        if submit_button:
            update_account_details(first_name, middle_name, last_name, profile_color)


with tabs[2]:
    show_account_tab()
