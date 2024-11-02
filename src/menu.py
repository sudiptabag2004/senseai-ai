import streamlit as st
from typing import Dict
import os


def menu_header():
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
        label="Home",
        icon="🏠",
    )


def show_links():
    with st.sidebar:
        st.page_link(
            "https://script.google.com/macros/s/AKfycbzfH42BZ5t8Yo9O1B23ELpM920EDwQ2_1ecOpk4OGqN3bMZ_FURie8uzHLtlKp-CooC/exec",
            label="Apply for a leave",
            icon="🏖️",
        )
        st.page_link(
            "https://script.google.com/a/macros/hyperverge.co/s/AKfycbz14hcx16xpn5DklkSa_n28tfIVi8v9oXzDHYJVBBcTwZIDZZ3s6QpBD7WLEyPhKrxc/exec?page=interview_scheduling",
            label="Apply for a mock interview",
            icon="🎙️",
        )
        st.page_link(
            "https://chromewebstore.google.com/detail/sentence-enhancer/gomkfbbonafokpdagofhfkhoaeamcjmf?authuser=0&hl=en",
            label="Sentence Enhancer",
            icon="😎",
        )
        st.page_link(
            "https://wa.me/916366309432",
            label="Power Up (your English skills)",
            icon="🗣️",
        )


def update_query_params(
    key,
):
    st.query_params[key] = int(st.session_state[key])


def menu_footer():
    st.sidebar.divider()

    if st.sidebar.checkbox(
        "I am a HyperVerge Academy learner",
        key="is_hv_learner",
        on_change=update_query_params,
        args=("is_hv_learner",),
    ):
        show_links()


def authenticated_menu(logged_in_user: Dict):
    with st.sidebar:
        st.page_link(
            f"{os.environ.get('APP_URL')}/profile?id={logged_in_user['id']}",
            label="Your Profile",
            icon="👔",
        )
        st.divider()

        st.markdown(
            """
            <div style="display: flex; align-items: flex-start; gap: 4px;">
                <h3 style="margin: 0;">Placement Prep</h3>
                <span style="background-color: #ffd700; padding: 1px 6px; border-radius: 4px; font-size: 0.6em; position: relative; top: 2px;">BETA</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

        st.page_link(
            f"{os.environ.get('APP_URL')}/mock_interview?id={logged_in_user['id']}",
            label="AI Mock Interview",
            icon="🎙️",
        )

        st.page_link(
            f"{os.environ.get('APP_URL')}/cv_review?id={logged_in_user['id']}",
            label="AI CV Review",
            icon="📄",
        )


def menu(logged_in_user: Dict):
    menu_header()
    if logged_in_user:
        authenticated_menu(logged_in_user)

    menu_footer()
    # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
