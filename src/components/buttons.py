import os
import streamlit as st


def back_to_home_button():
    home_page_url = os.environ.get("APP_URL")

    st.markdown(
        f'<a href="{home_page_url}" target="_self" style="color: white; text-decoration: none; background-color: rgba(49, 51, 63, 0.4); padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">🏠 Back to Home</a>',
        unsafe_allow_html=True,
    )
