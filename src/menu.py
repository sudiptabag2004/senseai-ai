import streamlit as st
from typing import Dict
import os
from lib.organization import show_create_org_dialog
from lib.toast import set_toast, show_toast
from auth import get_hva_org_id


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


def clear_auth():
    st.query_params.clear()
    st.session_state.user = None
    st.session_state.email = None
    st.rerun()


def menu_footer(selected_cohort: Dict, is_mentor: bool):
    st.sidebar.divider()

    if (
        not is_mentor
        and selected_cohort is not None
        and selected_cohort["org_id"] == get_hva_org_id()
    ):

        show_links()

        st.sidebar.divider()

    st.sidebar.text("Built with ❤️ by HyperVerge Academy")

    if st.session_state.email:
        if st.sidebar.button("Logout"):
            clear_auth()


def authenticated_menu(logged_in_user: Dict, selected_cohort: Dict, is_mentor: bool):
    with st.sidebar:
        # display_name = get_logged_in_user_display_name("first")
        # st.markdown(
        #     f"""
        #     <h3 style="margin: 0;">Welcome, {display_name}!</h3>
        #     """,
        #     unsafe_allow_html=True,
        # )
        st.page_link(
            f"{os.environ.get('APP_URL')}/profile?id={logged_in_user['id']}",
            label="Your Profile",
            icon="👔",
        )

        if (
            is_mentor
            or selected_cohort is None
            or selected_cohort["org_id"] != get_hva_org_id()
        ):
            cols = st.sidebar.columns([6, 1])
            selected_org = cols[0].selectbox(
                f'`{st.session_state["email"]}`',
                st.session_state.user_orgs,
                format_func=lambda val: f"{val['name']} ({val['role']})",
            )

            cols[1].container(height=10, border=False)
            cols[1].button(
                "",
                icon="➕",
                help="Create an organization",
                on_click=show_create_org_dialog,
                args=(logged_in_user["id"],),
            )

            st.page_link(
                f"{os.environ.get('APP_URL')}/admin?id={logged_in_user['id']}&org_id={selected_org['id']}",
                label="Admin Panel",
                icon="⚙️",
            )

            return

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
            f"{os.environ.get('APP_URL')}/interview_practice?id={logged_in_user['id']}",
            label="Practice for Interviews with AI",
            icon="🎙️",
        )

        st.page_link(
            f"{os.environ.get('APP_URL')}/cv_review?id={logged_in_user['id']}",
            label="Polish your CV with AI",
            icon="📄",
        )


def menu(logged_in_user: Dict, selected_cohort: Dict, is_mentor: bool):
    show_toast()
    menu_header()
    if logged_in_user:
        authenticated_menu(logged_in_user, selected_cohort, is_mentor)

    menu_footer(selected_cohort, is_mentor)
    # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
