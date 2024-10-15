import streamlit as st


def default_menu():
    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu():
    with st.sidebar:
        st.link_button(
            "👨‍💻👩‍💻 Start solving tasks",
            f"/task_list?email={st.session_state.email}",
        )
    pass


def menu():
    default_menu()
    if st.session_state.email:
        st.sidebar.divider()
        authenticated_menu()

        # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
