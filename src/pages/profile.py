import time
import streamlit as st

st.set_page_config(layout="wide")

from typing import Dict

from lib.db import get_user_by_id, update_user as update_user_in_db


if "id" not in st.query_params:
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")


def get_user_name(user: Dict) -> str:
    if not user["first_name"]:
        return ""

    middle_name = ""
    if user["middle_name"]:
        middle_name = f" {user['middle_name']}"

    full_name = f"{user['first_name']}{middle_name} {user['last_name']}"
    return full_name.strip()


def show_profile_icon(user: Dict):
    user_name = get_user_name(user)
    if user_name:
        initial = user_name[0].upper()
    else:
        initial = user["email"][0].upper()

    st.markdown(
        f"""
        <div style="width:150px;height:150px;border-radius:50%;background-color:{user['default_dp_color']};display:flex;justify-content:center;align-items:center;">
            <span style="font-size:72px;color:#333;">{initial}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def profile_header(user: Dict):
    cols = st.columns([1, 5])

    with cols[0]:
        show_profile_icon(user)

    with cols[1]:
        user_name = get_user_name(user)
        if user_name:
            st.header(user_name)
        st.markdown(user["email"])


# Assuming the user ID is passed in the query params
user_id = st.query_params.get("id")


def refresh_user():
    st.session_state.user = get_user_by_id(user_id)


refresh_user()

if not st.session_state.user:
    st.error("User not found")
    st.stop()

profile_header(st.session_state.user)

st.container(height=20, border=False)

tab_names = ["Account"]
tabs = st.tabs(tab_names)


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

    update_user_in_db(user_id, first_name, middle_name, last_name, profile_color)


with tabs[0]:
    with st.form("account_details", border=False):
        cols = st.columns(3)
        with cols[0]:
            first_name = st.text_input(
                "First Name*", value=st.session_state.user["first_name"]
            )

        with cols[1]:
            middle_name = st.text_input(
                "Middle Name", value=st.session_state.user["middle_name"]
            )

        with cols[2]:
            last_name = st.text_input(
                "Last Name*", value=st.session_state.user["last_name"]
            )

        cols = st.columns(2)
        with cols[0]:
            email = st.text_input(
                "Email", value=st.session_state.user["email"], disabled=True
            )

        with cols[1]:
            profile_color = st.color_picker(
                "Profile Color", value=st.session_state.user["default_dp_color"]
            )

        submit_button = st.form_submit_button("Save", type="primary")
        if submit_button:
            update_account_details(first_name, middle_name, last_name, profile_color)
            st.rerun()
