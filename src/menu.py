import streamlit as st
from typing import Dict
import os


def default_menu():
    st.logo("./lib/assets/logo.png")
    st.sidebar.markdown(
        """
        <p style='margin-top: -25px; margin-bottom: 15px; color: #1E2F4D'>
        Your personal AI tutor
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu(logged_in_user: Dict):
    with st.sidebar:
        st.page_link(
            f"{os.environ.get('APP_URL')}/profile?id={logged_in_user['id']}",
            label="👔 Your Profile",
        )
        st.divider()
        st.subheader("Placement Prep")
        st.link_button(
            "Mock Interview",
            f"/mock_interview?id={logged_in_user['id']}",
        )
        # st.link_button(
        #     "CV Interview",
        #     f"/cv_review?id={logged_in_user['id']}",
        # )


def menu(logged_in_user: Dict):
    default_menu()
    if logged_in_user:
        authenticated_menu(logged_in_user)

    # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
