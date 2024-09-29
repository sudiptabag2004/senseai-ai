import streamlit as st

st.set_page_config(layout="wide")

from email_validator import validate_email, EmailNotValidError
from menu import menu
from lib.init import init_db
from components.streak import show_streak

# init_auth_from_cookies()

init_db()

if "email" in st.query_params:
    st.session_state.email = st.query_params["email"]

st.title("SensAI - your personal AI tutor")

if "email" not in st.session_state:
    st.session_state.email = None


def clear_auth():
    st.query_params.clear()
    st.session_state.email = None
    st.rerun()


st.container(height=20, border=False)


def login():
    if not st.session_state.email:
        logged_in = False

        placeholder = st.empty()

        with placeholder.form("login_form"):
            email = st.text_input("Email")

            if st.form_submit_button("Login"):
                try:
                    # Check that the email address is valid. Turn on check_deliverability
                    # for first-time validations like on account creation pages (but not
                    # login pages).
                    emailinfo = validate_email(email, check_deliverability=True)

                    # After this point, use only the normalized form of the email address,
                    # especially before going to a database query.
                    st.session_state.email = emailinfo.normalized
                    st.query_params.email = st.session_state.email
                    # st.rerun()
                    logged_in = True

                except EmailNotValidError as e:
                    # The exception message is human-readable explanation of why it's
                    # not a valid (or deliverable) email address.
                    st.error("Invalid email")

        if logged_in:
            placeholder.empty()
            login()

    else:
        show_streak()
        st.markdown(f"Welcome `{st.session_state.email}`!")
        st.markdown(
            "Select one of the options from the sidebar on the left to get started.\n\nLet's begin learning! 🚀"
        )


login()

st.container(height=20, border=False)

st.divider()

st.text("Built with ❤️ by HyperVerge Academy")

if st.session_state.email:
    if st.button("Logout"):
        clear_auth()

menu()

if not st.query_params:
    st.query_params.clear()
