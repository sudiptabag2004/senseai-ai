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
    show_home()

if not st.query_params:
    st.query_params.clear()
