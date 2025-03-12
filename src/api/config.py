import os
from os.path import exists
from api.models import LeaderboardViewType, TaskInputType, TaskAIResponseType, TaskType

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
log_file_path = f"{log_dir}/backend.log"

chat_history_table_name = "chat_history"
tasks_table_name = "tasks"
questions_table_name = "questions"
blocks_table_name = "blocks"
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
