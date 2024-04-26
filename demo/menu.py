import streamlit as st
from auth import is_authorised


def default_menu():
    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu():
    st.sidebar.page_link(
        "pages/app.py",
        label="👨‍💻👩‍💻 Test your programming skills",
    )
    st.sidebar.page_link(
        "pages/english_new.py", label=" 📚👂🖊️ 🗣️ Hone your english skills"
    )


def menu():
    default_menu()
    if is_authorised():
        st.sidebar.divider()
        authenticated_menu()


def menu_with_redirect():
    if not is_authorised():
        st.switch_page("home.py")
    else:
        menu()
