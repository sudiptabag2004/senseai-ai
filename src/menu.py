import streamlit as st
import streamlit_page_link_params as stpl

def default_menu():
    st.sidebar.page_link(
        "home.py",
        label="🏠 Home",
    )


def authenticated_menu():
    with st.sidebar:
        stpl.page_link(
            "pages/task_list.py",
            label="👨‍💻👩‍💻 Start solving tasks",
            query_params={"email": st.session_state.email}
        )
    # st.sidebar.page_link(
    #     "pages/english_new.py", label=" 📚👂🖊️ 🗣️ Hone your english skills"
    # )
    pass


def menu():
    default_menu()
    if st.session_state.email:
        st.sidebar.divider()
        authenticated_menu()
        
        st.sidebar.markdown('#')
        st.sidebar.markdown('#')
        st.sidebar.markdown('#')

        # auth(label="Change your logged in email", key_suffix="menu",  sidebar=True)
        
