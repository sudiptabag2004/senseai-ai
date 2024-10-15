import os
from os.path import exists

# from lib.utils import save_json

if exists("/appdata"):
    data_root_dir = "/appdata"
    root_dir = "/demo"
else:
    data_root_dir = "./db"
    root_dir = os.path.dirname(os.path.abspath(__file__))


# tasks_db_path = f"{data_root_dir}/tasks.json"

# if not exists(tasks_db_path):
#     save_json(tasks_db_path, [])

sqlite_db_path = f"{data_root_dir}/db.sqlite"
chat_history_table_name = "chat_history"
tasks_table_name = "tasks"
tests_table_name = "tests"
cohorts_table_name = "cohorts"
groups_table_name = "groups"
user_groups_table_name = "user_groups"

group_role_learner = "learner"
group_role_mentor = "mentor"

coding_languages_supported = ["HTML", "CSS", "Javascript", "NodeJS", "Python"]
