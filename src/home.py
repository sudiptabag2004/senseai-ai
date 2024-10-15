import streamlit as st

st.set_page_config(layout="wide")

from email_validator import validate_email, EmailNotValidError
from menu import menu
from lib.init import init_db
from components.streak import show_streak
from components.leaderboard import show_leaderboard

# init_auth_from_cookies()

init_db()

if "email" in st.query_params:
    st.session_state.email = st.query_params["email"]

if "is_hv_learner" in st.query_params:
    st.session_state.is_hv_learner = int(st.query_params["is_hv_learner"])

st.title("SensAI - your personal AI tutor")

if "email" not in st.session_state:
    st.session_state.email = None

if "is_hv_learner" not in st.session_state:
    st.session_state.is_hv_learner = False


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
        cols = st.columns([4, 3])
        with cols[0]:
            st.markdown(f"Welcome `{st.session_state.email}`! Let's begin learning! 🚀")
            st.link_button(
                "👨‍💻👩‍💻 Start solving tasks",
                f"/task_list?email={st.session_state.email}",
            )

        with cols[1]:
            show_streak()
            show_leaderboard()


login()

menu()


def show_links():
    st.sidebar.link_button(
        "🏖️ Apply for a leave",
        "https://script.google.com/macros/s/AKfycbzfH42BZ5t8Yo9O1B23ELpM920EDwQ2_1ecOpk4OGqN3bMZ_FURie8uzHLtlKp-CooC/exec",
    )
    st.sidebar.link_button(
        "🎙️ Apply for a mock interview",
        "https://script.google.com/a/macros/hyperverge.co/s/AKfycbz14hcx16xpn5DklkSa_n28tfIVi8v9oXzDHYJVBBcTwZIDZZ3s6QpBD7WLEyPhKrxc/exec?page=interview_scheduling",
    )
    st.sidebar.link_button(
        "😎 Sentence Enhancer",
        "https://chromewebstore.google.com/detail/sentence-enhancer/gomkfbbonafokpdagofhfkhoaeamcjmf?authuser=0&hl=en",
    )
    st.sidebar.link_button(
        "🗣️ Power Up (your English skills)",
        "https://wa.me/916366309432",
        help="Text `English` to get started",
    )


st.sidebar.divider()


def update_query_params(
    key,
):
    st.query_params[key] = int(st.session_state[key])


if st.sidebar.checkbox(
    "I am a HyperVerge Academy learner",
    key="is_hv_learner",
    on_change=update_query_params,
    args=("is_hv_learner",),
):
    show_links()


def show_footer():
    st.sidebar.divider()

    st.sidebar.text("Built with ❤️ by HyperVerge Academy")

    if st.session_state.email:
        if st.sidebar.button("Logout"):
            clear_auth()


show_footer()

if not st.query_params:
    st.query_params.clear()
