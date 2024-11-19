import streamlit as st
from lib.utils import generate_random_color
from lib.db import create_organization_with_user
from lib.toast import set_toast
from auth import update_user_orgs


@st.dialog("Create an organization")
def show_create_org_dialog(user_id: int):
    with st.form("create_org", border=False):
        cols = st.columns([5, 1])
        with cols[0]:
            org_name = st.text_input(
                "Organization Name*",
                key="org_name",
                value=st.session_state.user["first_name"],
            )

        color = generate_random_color()

        with cols[1]:
            logo_color = st.color_picker(
                "Logo Color",
                value=color,
                key="logo_color",
            )

        submit_button = st.form_submit_button(
            "Create",
            use_container_width=True,
            type="primary",
        )
        if submit_button:
            create_organization_with_user(org_name, user_id, logo_color)
            update_user_orgs(st.session_state.user)
            set_toast("Organization created successfully")
            st.rerun()
