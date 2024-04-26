import streamlit as st
from email_validator import validate_email, EmailNotValidError

from menu import menu
from auth import is_authorised, set_auth_state, maintain_auth_state

st.title("Welcome to SensAI")
st.subheader("SensAI is your personal AI tutor")

st.markdown("#")


if not is_authorised():

    def validate_and_norm_email():
        try:
            # Check that the email address is valid. Turn on check_deliverability
            # for first-time validations like on account creation pages (but not
            # login pages).
            emailinfo = validate_email(
                st.session_state.email, check_deliverability=True
            )

            # After this point, use only the normalized form of the email address,
            # especially before going to a database query.
            email = emailinfo.normalized
            set_auth_state(email)

        except EmailNotValidError as e:
            # The exception message is human-readable explanation of why it's
            # not a valid (or deliverable) email address.
            st.error("Invalid email")

    email = st.text_input("Enter your email to log in", key="email")
    email_submit_button = st.button("Submit", on_click=validate_and_norm_email)

else:
    maintain_auth_state()
    st.markdown(
        "Select one of the options from the sidebar on the left to get started.\n\nLet's begin learning! 🚀"
    )


st.markdown("#")

st.divider()

st.text("Built with ❤️ by HyperVerge Academy")

menu()
