import streamlit as st
from typing import Dict


def default_menu():
    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu(logged_in_user: Dict):
    with st.sidebar:
        st.link_button(
            "Your Profile",
            f"/profile?id={logged_in_user['id']}",
        )


def menu(logged_in_user: Dict):
    default_menu()
    if logged_in_user:
        authenticated_menu(logged_in_user)

    # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
