import streamlit as st

st.set_page_config(layout="wide")

from auth import login_or_signup_user, get_logged_in_user, login
from lib.init import init_app
from views.home import show_home

# init_auth_from_cookies()

init_app()

if "email" in st.query_params:
    login_or_signup_user(st.query_params["email"])

if "email" not in st.session_state:
    st.session_state.email = None

logged_in_user = get_logged_in_user()


if not logged_in_user:
    login()
else:
    show_home()

if not st.query_params:
    st.query_params.clear()
