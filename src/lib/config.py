import os
from os.path import exists
from lib.utils import save_json
from models import LeaderboardViewType, TaskInputType, TaskAIResponseType, TaskType

if exists("/appdata"):
    data_root_dir = "/appdata"
    root_dir = "/demo"
    log_dir = "/appdata/logs"
else:
    data_root_dir = "./db"
    root_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = "./logs"

if not exists(data_root_dir):
    os.makedirs(data_root_dir)

if not exists(log_dir):
    os.makedirs(log_dir)

sqlite_db_path = f"{data_root_dir}/db.sqlite"
log_file_path = f"{log_dir}/app.log"

chat_history_table_name = "chat_history"
tasks_table_name = "tasks"
tests_table_name = "tests"
cohorts_table_name = "cohorts"
course_tasks_table_name = "course_tasks"
course_milestones_table_name = "course_milestones"
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

uncategorized_milestone_name = "[UNASSIGNED]"
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
all_input_types = [
    str(TaskInputType.TEXT),
    str(TaskInputType.AUDIO),
    str(TaskInputType.CODING),
]
all_ai_response_types = [
    str(TaskAIResponseType.CHAT),
    str(TaskAIResponseType.REPORT),
    str(TaskAIResponseType.EXAM),
]
all_task_types = [str(TaskType.QUESTION), str(TaskType.READING_MATERIAL)]

response_type_help_text = """`chat`: AI provides feedback on the student's response and asks questions to nudge them towards the solution\n\n`report`: AI generates a report on the student's response based on a scoring criteria set by you\n\n`exam`: AI checks if the the student's response matches the reference solution without providing any further guidance"""

allowed_ai_response_types = {
    str(TaskInputType.CODING): [
        str(TaskAIResponseType.CHAT),
        str(TaskAIResponseType.REPORT),
        str(TaskAIResponseType.EXAM),
    ],
    str(TaskInputType.TEXT): [
        str(TaskAIResponseType.CHAT),
        str(TaskAIResponseType.REPORT),
        str(TaskAIResponseType.EXAM),
    ],
    str(TaskInputType.AUDIO): [str(TaskAIResponseType.REPORT)],
}

task_type_mapping = [
    {"label": "Question", "value": str(TaskType.QUESTION)},
    {"label": "Reading Material", "value": str(TaskType.READING_MATERIAL)},
]
task_type_to_label = {
    task_type["value"]: task_type["label"] for task_type in task_type_mapping
}

PDF_PAGE_DIMS = [595, 842]

MAX_TASK_NAME_LENGTH = 100

openai_plan_to_model_name = {
    "paid": {
        "4o-text": "gpt-4o-2024-11-20",
        "4o-audio": "gpt-4o-audio-preview-2024-12-17",
    },
    "free_trial": {
        "4o-text": "gpt-4o-mini-2024-07-18",
        "4o-audio": "gpt-4o-mini-audio-preview-2024-12-17",
    },
}
