import os
import streamlit as st
from lib.init import init_app
from auth import get_logged_in_user

init_app()


def back_to_home_button():
    app_url = os.environ.get("APP_URL")
    logged_in_user = get_logged_in_user()
    home_page_url = f"{app_url}/?email={logged_in_user['email']}"

    st.markdown(
        f'<a href="{home_page_url}" target="_self" style="color: white; text-decoration: none; background-color: rgba(49, 51, 63, 0.4); padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">🏠 Back to Home</a>',
        unsafe_allow_html=True,
    )
