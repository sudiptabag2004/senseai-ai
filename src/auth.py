import streamlit as st
import time
from typing import Dict
from lib.db import (
    insert_or_return_user,
    get_user_organizations,
    get_org_by_id,
)


def update_user_orgs(user: Dict):
    st.session_state.user_orgs = get_user_organizations(user["id"])


def set_logged_in_user_orgs(user: Dict):
    if "user_orgs" in st.session_state:
        return

    update_user_orgs(user)


def login_or_signup_user(email: str, given_name: str = None, family_name: str = None):
    if "user" in st.session_state:
        return st.session_state.user

    st.session_state.email = email
    st.session_state.user = insert_or_return_user(email, given_name, family_name)
    set_logged_in_user_orgs(st.session_state.user)


def unauthorized_redirect_to_home(
    error_message: str = "Not authorized. Redirecting to home page...",
):
    st.error(error_message)
    time.sleep(2)
    st.switch_page("./home.py")


def redirect_if_not_logged_in():
    if not st.experimental_user.is_authenticated:
        unauthorized_redirect_to_home()


def login():
    cols = st.columns([2, 3, 1])

    if st.session_state.theme["base"] == "dark":
        logo_path = "./lib/assets/dark_logo.svg"
        subtitle_color = "#fff"
    else:
        logo_path = "./lib/assets/light_logo.svg"
        subtitle_color = "#1E2F4D"

    cols[1].image(logo_path, width=400)

    cols[1].markdown(
        f"""
        <p style='margin-top: 20px; margin-left: 40px; font-size: 2rem; color: {subtitle_color}'>
        Your personal AI tutor
        </p>
        """,
        unsafe_allow_html=True,
    )

    cols[1].container(height=20, border=False)

    sub_cols = cols[1].columns([0.6, 1])
    google_button = sub_cols[0].button("Sign up or Sign in with Google", type="primary")

    if google_button:
        st.experimental_user.login(provider="google")

    sub_cols[-1].link_button(
        "See Documentation", "https://hypervergeacademy.mintlify.app/"
    )


def get_org_details_from_org_id(org_id: int):
    if "org_details" not in st.session_state:
        st.session_state.org_details = {}

    if org_id in st.session_state.org_details:
        return st.session_state.org_details[org_id]

    org_details = get_org_by_id(org_id)
    st.session_state.org_details[org_id] = org_details
    return org_details
