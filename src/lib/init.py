import os
from os.path import join
from dotenv import load_dotenv
from lib.db import init_db

root_dir = os.path.dirname(os.path.abspath(__file__))


def init_env_vars():
    load_dotenv(join(root_dir, ".env"))


def init_app():
    init_env_vars()
    init_db()
