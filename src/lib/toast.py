import streamlit as st


def init_toast_params():
    if "show_toast" not in st.session_state:
        st.session_state.show_toast = False

    if "toast_message" not in st.session_state:
        st.session_state.toast_message = ""


def set_toast(message: str):
    if not message:
        return

    st.session_state.show_toast = True
    st.session_state.toast_message = message


def show_toast():
    init_toast_params()
    if st.session_state.show_toast:
        st.toast(st.session_state.toast_message)
        st.session_state.show_toast = False
