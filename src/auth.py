import streamlit as st
import time
from email_validator import validate_email, EmailNotValidError
from lib.db import upsert_user, get_user_by_email, get_user_by_id


def login_or_signup_user(email: str):
    st.session_state.email = email
    upsert_user(email)


def get_logged_in_user():
    if "email" not in st.session_state and "id" not in st.session_state:
        return None

    if "email" in st.session_state:
        return get_user_by_email(st.session_state.email)
    else:
        return get_user_by_id(st.session_state.id)


def unauthorized_redirect_to_home():
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")


def set_logged_in_user(value: str, key: str = "email", dtype: type = str):
    if dtype == int:
        st.session_state[key] = int(value)
    else:
        st.session_state[key] = value


def redirect_if_not_logged_in(key: str = "email"):
    if key not in st.query_params:
        unauthorized_redirect_to_home()
    else:
        key_dtype = int if key == "id" else str
        set_logged_in_user(st.query_params[key], key, key_dtype)


def login():
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
                login_or_signup_user(emailinfo.normalized)
                st.query_params.email = st.session_state.email
                # st.rerun()
                logged_in = True

            except EmailNotValidError as e:
                # The exception message is human-readable explanation of why it's
                # not a valid (or deliverable) email address.
                st.error("Invalid email")

    if logged_in:
        placeholder.empty()
        st.rerun()
