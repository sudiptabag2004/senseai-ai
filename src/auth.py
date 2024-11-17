import streamlit as st
import time
from typing import Literal, Dict
from email_validator import validate_email, EmailNotValidError
from lib.db import upsert_user, get_user_by_email, get_user_by_id
from lib.profile import get_display_name_for_user


def login_or_signup_user(email: str):
    st.session_state.email = email
    st.session_state.user = upsert_user(email)


def get_logged_in_user():
    # TODO: when logged in, set session_state.id and use that everywhere or return it from here or something like that
    # TODO: add a cache to avoid making DB calls and invalidate cache when user logs out or when user changes their profile details
    if "user" in st.session_state and st.session_state.user:
        return st.session_state.user

    if "email" not in st.session_state and "id" not in st.session_state:
        return None

    if "email" in st.session_state:
        st.session_state.user = get_user_by_email(st.session_state.email)
    else:
        st.session_state.user = get_user_by_id(st.session_state.id)

    return st.session_state.user


def unauthorized_redirect_to_home():
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")


def set_logged_in_user(
    value: str,
    key: str = "email",
):
    if key == "id":
        value = int(value)
        st.session_state[key] = value
        st.session_state.user = get_user_by_id(value)
    else:
        st.session_state[key] = value
        st.session_state.user = get_user_by_email(value)


def redirect_if_not_logged_in(key: str = "email"):
    if key not in st.query_params:
        unauthorized_redirect_to_home()
    else:
        set_logged_in_user(st.query_params[key], key)


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


def get_logged_in_user_display_name(name_type: Literal["full", "first"] = "full"):
    user = get_logged_in_user()
    return get_display_name_for_user(user, name_type)
