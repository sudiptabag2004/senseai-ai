import streamlit as st

st.set_page_config(layout="wide")
from auth import (
    redirect_if_not_logged_in,
    unauthorized_redirect_to_home,
    get_logged_in_user,
)
from views.roadmap import get_tasks_with_completion_status, show_roadmap_as_list

redirect_if_not_logged_in()

if (
    "mode" not in st.query_params
    or st.query_params["mode"] != "review"
    or "learner" not in st.query_params
):
    unauthorized_redirect_to_home()


logged_in_user = get_logged_in_user()


if "milestone_id" in st.query_params:
    milestone_id = int(st.query_params["milestone_id"])
else:
    milestone_id = None

all_tasks = get_tasks_with_completion_status(
    st.query_params["learner"],
    milestone_id,
)

show_roadmap_as_list(
    all_tasks, is_review_mode=True, learner_email=st.query_params["learner"]
)
