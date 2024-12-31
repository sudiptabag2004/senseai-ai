import streamlit as st

st.set_page_config(layout="wide", page_title="Roadmap | SensAI")
from lib.init import init_app
from auth import (
    redirect_if_not_logged_in,
    unauthorized_redirect_to_home,
    login_or_signup_user,
)
from views.roadmap import get_tasks_with_completion_status, show_roadmap_as_list

init_app()
redirect_if_not_logged_in()
login_or_signup_user(st.experimental_user["email"])

if (
    "mode" not in st.query_params
    or st.query_params["mode"] != "review"
    or "learner" not in st.query_params
    or "course" not in st.query_params
    or "cohort" not in st.query_params
):
    unauthorized_redirect_to_home()


if "milestone_id" in st.query_params:
    milestone_id = int(st.query_params["milestone_id"])
else:
    milestone_id = None

cohort_id = int(st.query_params["cohort"])
course_id = int(st.query_params["course"])

all_tasks = get_tasks_with_completion_status(
    st.query_params["learner"],
    cohort_id,
    course_id,
    milestone_id,
)

show_roadmap_as_list(
    all_tasks,
    cohort_id,
    course_id,
    is_review_mode=True,
    learner_id=st.query_params["learner"],
)
