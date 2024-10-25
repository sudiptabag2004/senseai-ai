import streamlit as st
from lib.db import upsert_user, get_user_by_email


def login_or_signup_user(email: str):
    st.session_state.email = email
    upsert_user(email)


def get_logged_in_user():
    if "email" not in st.session_state:
        return None

    return get_user_by_email(st.session_state.email)
