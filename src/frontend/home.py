import streamlit as st

st.set_page_config(layout="wide", page_title="Home | SensAI")

from lib.init import init_app

init_app()

from auth import login_or_signup_user, login
from views.home import show_home
from components.status import error_markdown
from components.buttons import back_to_home_button
from lib.cohort import add_members_to_cohort
from lib.toast import set_toast, show_toast
from lib.config import group_role_learner

show_toast()

st.markdown(
    """
        <style>
            .stMainBlockContainer {
                padding-top: 3rem;
                }
        </style>""",
    unsafe_allow_html=True,
)

if not st.experimental_user.is_authenticated:
    login()
else:
    login_or_signup_user()

    if st.query_params:
        if "cohort_id_to_join" in st.query_params:
            try:
                with st.spinner("Joining cohort..."):
                    cohort_id_to_join = int(st.query_params["cohort_id_to_join"])
                    add_members_to_cohort(
                        cohort_id_to_join,
                        [st.session_state.user["email"]],
                        [group_role_learner],
                    )
                    set_toast("You have been added to the cohort", icon="👋")
            except Exception:
                pass

            st.query_params.clear()
            st.rerun()

        if "org_id" in st.query_params:
            # make sure that if someone is coming from the admin panel to the home page,
            # the selected org is the one they came from
            st.session_state.org_id = int(st.query_params["org_id"])

            selected_org = [
                org
                for org in st.session_state.user_orgs
                if org["id"] == st.session_state.org_id
            ]

            if not selected_org:
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    st.markdown(
                        """<h1 style='text-align: center; color: #ff4b4b; font-size: 2rem; margin-bottom: 2rem;'>
                        🚫 Access Denied
                        </h1>""",
                        unsafe_allow_html=True,
                    )
                    error_markdown(
                        """<div style='text-align: center; font-size: 1.1rem;'>
                        You are not a part of this organization. Please ask your admin to <a href="https://docs.sensai.hyperverge.org/guides/organizations#add-members-to-an-organization" target="_self">add</a> you to the organization.
                        <br><br>
                        If you are the admin and want to share a course with a learner, you need to <a href="https://docs.sensai.hyperverge.org/guides/cohorts#add-members-to-a-cohort" target="_self">add</a> them to a cohort that has been assigned to the course.
                        </div>"""
                    )

                    st.container(height=10, border=False)
                    sub_cols = st.columns([1.5, 1, 1.5])
                    with sub_cols[1]:
                        back_to_home_button()

                st.stop()
                # error_markdown(
                #     """You are not a part of this organization. Please ask your admin to <a href="https://docs.sensai.hyperverge.org/guides/organizations#add-members-to-an-organization" target="_self">add</a> you to the organization. If you are the admin and want to share a course with a learner, you need to <a href="https://docs.sensai.hyperverge.org/guides/cohorts#add-members-to-a-cohort" target="_self">add</a> them to a cohort that has been assigned to the course."""
                # )
                # st.stop()

            st.session_state.selected_org = selected_org[0]

            # st.query_params.clear()

    show_home()
