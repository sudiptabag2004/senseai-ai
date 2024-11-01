import streamlit as st

st.set_page_config(page_title="Mock Interview | SensAI", layout="wide")

from auth import redirect_if_not_logged_in

redirect_if_not_logged_in(key="id")

if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0


def update_file_uploader_key():
    st.session_state.file_uploader_key += 1


st.file_uploader(
    "Upload your CV (PDF)",
    key=f"file_uploader_{st.session_state.file_uploader_key}",
    type="pdf",
)
