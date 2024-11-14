import streamlit as st


def select_role(is_disabled: bool = False):
    st.selectbox(
        "Select the role you want to apply for",
        disabled=is_disabled,
        key="selected_role",
        options=[
            "Frontend Developer",
            "Backend Developer",
            "Full Stack Developer",
            "UI/UX Designer",
            "Data Analyst",
            "Quality Assurance",
            "Other",
        ],
        index=None,
    )

    if st.session_state.selected_role == "Other":
        st.text_input(
            "Please specify",
            key="other_role",
            disabled=is_disabled,
        )


def get_selected_role():
    if st.session_state.selected_role == "Other":
        return st.session_state.other_role

    return st.session_state.selected_role
