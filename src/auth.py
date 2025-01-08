import streamlit as st
import time
from typing import Dict
from lib.db import (
    insert_or_return_user,
    get_user_organizations,
)


def update_user_orgs(user: Dict):
    st.session_state.user_orgs = get_user_organizations(user["id"])


def login_or_signup_user(email: str, given_name: str = None, family_name: str = None):
    if "user" not in st.session_state:
        st.session_state.email = email
        st.session_state.user = insert_or_return_user(email, given_name, family_name)

    update_user_orgs(st.session_state.user)

    return st.session_state.user


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

    sub_cols[-1].link_button("See Documentation", "docs.sensai.hyperverge.org/")
