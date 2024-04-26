import streamlit as st


def is_authorised():
    return "email" in st.session_state and st.session_state.email


def maintain_auth_state():
    st.session_state.email = st.session_state.email


def set_auth_state(email):
    st.session_state.email = email
