import streamlit as st

st.set_page_config(layout="wide", page_title="Home | SensAI")

from lib.init import init_app

init_app()

from auth import login_or_signup_user, login
from views.home import show_home

if not st.experimental_user.is_authenticated:
    login()
else:
    login_or_signup_user()

    if st.query_params:
        if "org_id" in st.query_params:
            # make sure that if someone is coming from the admin panel to the home page,
            # the selected org is the one they came from
            st.session_state.org_id = int(st.query_params["org_id"])

            st.session_state.selected_org = [
                org
                for org in st.session_state.user_orgs
                if org["id"] == st.session_state.org_id
            ][0]

            # st.query_params.clear()

    show_home()
