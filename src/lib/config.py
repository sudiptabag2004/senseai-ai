import os
from os.path import exists
from lib.utils import save_json
from models import LeaderboardViewType

if exists("/appdata"):
    data_root_dir = "/appdata"
    root_dir = "/demo"
else:
    data_root_dir = "./db"
    if not exists(data_root_dir):
        os.makedirs(data_root_dir)
    root_dir = os.path.dirname(os.path.abspath(__file__))

tags_list_path = f"{data_root_dir}/tags.json"

sqlite_db_path = f"{data_root_dir}/db.sqlite"

chat_history_table_name = "chat_history"
tasks_table_name = "tasks"
tests_table_name = "tests"
cohorts_table_name = "cohorts"
course_tasks_table_name = "course_tasks"
courses_table_name = "courses"
course_cohorts_table_name = "course_cohorts"
task_scoring_criteria_table_name = "task_scoring_criteria"
groups_table_name = "groups"
user_cohorts_table_name = "user_cohorts"
user_groups_table_name = "user_groups"
milestones_table_name = "milestones"
tags_table_name = "tags"
task_tags_table_name = "task_tags"
users_table_name = "users"
badges_table_name = "badges"
cv_review_usage_table_name = "cv_review_usage"
organizations_table_name = "organizations"
user_organizations_table_name = "user_organizations"

group_role_learner = "learner"
group_role_mentor = "mentor"

uncategorized_milestone_name = "Uncategorized"
uncategorized_milestone_color = "#808080"

coding_languages_supported = [
    "HTML",
    "CSS",
    "Javascript",
    "NodeJS",
    "Python",
    "React",
    "SQL",
]
leaderboard_view_types = [
    str(LeaderboardViewType.ALL_TIME),
    str(LeaderboardViewType.WEEKLY),
    str(LeaderboardViewType.MONTHLY),
]
task_input_types = ["coding", "text"]
task_ai_response_types = ["chat", "report"]

allowed_input_types = {
    "chat": ["coding", "text"],
    "report": ["text"],
}

PDF_PAGE_DIMS = [595, 842]
