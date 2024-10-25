import streamlit as st
from lib.db import upsert_user


def login_or_signup_user(email: str):
    st.session_state.email = email
    upsert_user(email)
