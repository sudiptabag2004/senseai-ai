from os.path import exists
from lib.utils import save_json

if exists("/appdata"):
    root_dir = "/appdata"
else:
    root_dir = "./db"


tasks_db_path = f"{root_dir}/tasks.json"

if not exists(tasks_db_path):
    save_json(tasks_db_path, [])