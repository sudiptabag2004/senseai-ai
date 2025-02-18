import streamlit as st
import time
import os
from typing import Dict
from lib.db import (
    insert_or_return_user,
    get_user_organizations,
)
from lib.config import pitch
from lib.utils.encryption import decrypt_openai_api_key


def is_empty_openai_api_key() -> bool:
    return not st.session_state.org["openai_api_key"]


def is_free_trial_openai_api_key() -> bool:
    return st.session_state.org["openai_free_trial"]


def update_user_orgs(user: Dict):
    st.session_state.user_orgs = get_user_organizations(user["id"])


def login_or_signup_user():
    redirect_if_not_logged_in()

    if "user" not in st.session_state:
        st.session_state.email = st.experimental_user.email

        st.session_state.user = insert_or_return_user(
            st.experimental_user.email,
            st.experimental_user.given_name,
            st.experimental_user.get("family_name"),
        )

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
    if st.session_state.theme["base"] == "dark":
        logo_path = "./lib/assets/dark_logo.svg"
        subtitle_color = "#fff"
        background_color = "#090D0E"
        feature_images_folder = "dark"
    else:
        logo_path = "./lib/assets/light_logo.svg"
        subtitle_color = "#1E2F4D"
        background_color = "#FFFFFF"
        feature_images_folder = "light"

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {background_color};
        }}
        .stAppHeader {{
            background-color: {background_color};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns([0.9, 0.1, 2, 0.1, 0.9])

    cols[2].image(f"./lib/assets/features/{feature_images_folder}/1.png")
    cols[2].container(height=20, border=False)

    cols[0].container(height=100, border=False)
    cols[0].image(f"./lib/assets/features/{feature_images_folder}/2_1.png")
    cols[0].image(f"./lib/assets/features/{feature_images_folder}/2_2.png")

    sub_cols = cols[2].columns([1, 2, 1])
    sub_cols[1].image(logo_path)

    sub_cols = cols[2].columns([1, 5, 1])
    sub_cols[1].markdown(
        f"""
        <p style='margin-top: 10px; font-size: 1.25rem; color: {subtitle_color}'>
        {pitch}
        </p>
        """,
        unsafe_allow_html=True,
    )

    cols[2].container(height=20, border=False)

    sub_cols = cols[2].columns(2)
    google_button = sub_cols[0].button(
        "Sign up or Sign in with Google", type="primary", use_container_width=True
    )

    if google_button:
        st.experimental_user.login(provider="google")

    sub_cols[-1].link_button(
        "See Documentation",
        "https://docs.sensai.hyperverge.org/",
        use_container_width=True,
    )

    cols[-1].container(height=100, border=False)
    cols[-1].image(f"./lib/assets/features/{feature_images_folder}/3_1.png")
    cols[-1].image(f"./lib/assets/features/{feature_images_folder}/3_2.png")

    cols[2].container(height=20, border=False)
    cols[2].image(f"./lib/assets/features/{feature_images_folder}/4.png")
