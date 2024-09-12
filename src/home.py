import streamlit as st
from auth import (
    is_authorised,
    auth,
    maintain_auth_state,
    init_auth_from_cookies,
)
from menu import menu
from lib.init import init_db

init_auth_from_cookies()

init_db()

st.title("SensAI - your personal AI tutor")

st.markdown("#")


if not is_authorised():
    auth(label="Enter your email to log in", key_suffix="home")
else:
    maintain_auth_state()
    st.markdown(f"Welcome `{st.session_state.email}`!")
    st.markdown(
        "Select one of the options from the sidebar on the left to get started.\n\nLet's begin learning! 🚀"
    )

st.markdown("#")

st.divider()

st.text("Built with ❤️ by HyperVerge Academy")

menu()
