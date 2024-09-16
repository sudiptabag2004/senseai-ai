import streamlit as st
st.set_page_config(layout="wide")

from email_validator import validate_email, EmailNotValidError
from menu import menu
from lib.init import init_db

# init_auth_from_cookies()

init_db()

st.title("SensAI - your personal AI tutor")

st.markdown("#")

if 'email' not in st.session_state:
    st.session_state.email = None

def clear_auth():
    st.session_state.email = None

if not st.session_state.email:
    with st.form('login_form'):
        email = st.text_input('Email')
        
        if st.form_submit_button('Login'):
            try:
                # Check that the email address is valid. Turn on check_deliverability
                # for first-time validations like on account creation pages (but not
                # login pages).
                emailinfo = validate_email(
                    email, check_deliverability=True
                )

                # After this point, use only the normalized form of the email address,
                # especially before going to a database query.
                st.session_state.email = emailinfo.normalized
                st.rerun()

            except EmailNotValidError as e:
                # The exception message is human-readable explanation of why it's
                # not a valid (or deliverable) email address.
                st.error("Invalid email")

# if not is_authorised():
#     auth(label="Enter your email to log in", key_suffix="home")
# else:
#     maintain_auth_state()
else:
    st.markdown(f"Welcome `{st.session_state.email}`!")
    st.markdown(
        "Select one of the options from the sidebar on the left to get started.\n\nLet's begin learning! 🚀"
    )

    st.markdown("#")
    if st.button("Logout"):
        clear_auth()
        st.rerun()

    
st.markdown("#")

st.divider()

st.text("Built with ❤️ by HyperVerge Academy")

menu()
