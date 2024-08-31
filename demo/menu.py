import streamlit as st
from auth import is_authorised, auth


def default_menu():
    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu():
    st.sidebar.page_link(
        "pages/task_list.py",
        label="👨‍💻👩‍💻 Start solving tasks",
    )
    # st.sidebar.page_link(
    #     "pages/english_new.py", label=" 📚👂🖊️ 🗣️ Hone your english skills"
    # )
    pass


def menu():
    default_menu()
    if is_authorised():
        st.sidebar.divider()
        authenticated_menu()
        
        st.sidebar.markdown('#')
        st.sidebar.markdown('#')
        st.sidebar.markdown('#')
        # st.sidebar.button("Logout", on_click=clear_auth)
        auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
        


def menu_with_redirect():
    if not is_authorised():
        st.switch_page("home.py")
    else:
        menu()
