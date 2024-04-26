import streamlit as st
from streamlit_cookies_manager import CookieManager
from email_validator import validate_email, EmailNotValidError


class Cookies:
    def __init__(self) -> None:
        self.cookie_manager = CookieManager()
        # self.cookie_manager._default_expiry = datetime.now() + timedelta(minutes=1)

        if not self.cookie_manager.ready():
            st.stop()

    def set_cookie(self, cookie_name, cookie_content):
        self.cookie_manager[cookie_name] = cookie_content
        self.cookie_manager.save()

    def get_cookie(self, cookie_name):
        value = self.cookie_manager.get(cookie_name)
        return value

    def delete_cookie(self, cookie_name):
        del self.cookie_manager[cookie_name]
        # st.write(f"del: {value}")


cookies = Cookies()

AUTH_COOKIES_NAME = "email"


def init_auth_from_cookies():
    if email := cookies.get_cookie(AUTH_COOKIES_NAME):
        st.session_state.email = email


init_auth_from_cookies()


def is_authorised():
    return "email" in st.session_state and st.session_state.email


def maintain_auth_state():
    st.session_state.email = st.session_state.email


def set_auth_state(email):
    st.session_state.email = email
    cookies.set_cookie(AUTH_COOKIES_NAME, email)


def auth(label: str, key_suffix: str, sidebar: bool = False):
    if sidebar:
        layout_fn = st.sidebar
    else:
        layout_fn = st

    email_key = f"email_{key_suffix}"

    def validate_and_norm_email():
        try:
            # Check that the email address is valid. Turn on check_deliverability
            # for first-time validations like on account creation pages (but not
            # login pages).
            emailinfo = validate_email(
                st.session_state[f"email_{key_suffix}"], check_deliverability=True
            )

            # After this point, use only the normalized form of the email address,
            # especially before going to a database query.
            email = emailinfo.normalized
            set_auth_state(email)

        except EmailNotValidError as e:
            # The exception message is human-readable explanation of why it's
            # not a valid (or deliverable) email address.
            st.error("Invalid email")

    initial_email = "" if not is_authorised() else st.session_state.email
    email = layout_fn.text_input(label=label, value=initial_email, key=email_key)
    email_submit_button = layout_fn.button(
        f"Submit_{key_suffix}", on_click=validate_and_norm_email
    )


def clear_auth():
    st.session_state.email = None
    # cookies.delete_cookie(AUTH_COOKIES_NAME)
