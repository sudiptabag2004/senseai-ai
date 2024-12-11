import os
from os.path import join
from dotenv import load_dotenv
from lib.db import init_db
import streamlit as st
from streamlit_theme import st_theme
from lib.llm import logger

root_dir = os.path.dirname(os.path.abspath(__file__))


def init_theme():
    theme = st_theme()
    if not theme:
        theme = {"base": "light"}

    st.session_state.theme = theme


def init_env_vars():
    load_dotenv(join(root_dir, ".env"))

    if os.path.exists(join(root_dir, ".env.aws")):
        load_dotenv(join(root_dir, ".env.aws"))


def init_app():
    init_theme()
    init_env_vars()
    init_db()
