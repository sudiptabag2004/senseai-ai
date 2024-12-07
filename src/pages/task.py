from typing import List, Literal
import os
import time
import json
from copy import deepcopy

import streamlit as st

st.set_page_config(
    page_title="Task | SensAI", layout="wide", initial_sidebar_state="collapsed"
)

from lib.llm import logger, get_formatted_history
from components.buttons import back_to_home_button
from auth import login_or_signup_user
from lib.config import uncategorized_milestone_name
from lib.db import (
    get_task_by_id,
    store_message as store_message_to_db,
    get_task_chat_history_for_user,
    get_user_streak,
    get_badge_by_type_and_user_id,
    get_scoring_criteria_for_task,
    get_cohort_by_id,
)
from lib.output_formats.report import (
    get_ai_report_response,
    show_ai_report,
    show_attempt_picker,
    reset_displayed_attempt_index,
    set_display_for_new_attempt,
    reset_current_num_attempts,
    increase_current_num_attempts,
    set_display_for_restoring_history,
    get_containers as get_report_containers,
    display_user_text_input_report,
    display_user_audio_input_report,
)
from lib.output_formats.chat import (
    get_containers as get_chat_containers,
    display_user_chat_message,
    get_ai_chat_response,
)
from lib.ui import (
    cleanup_ai_response,
)
from lib.s3 import (
    upload_audio_data_to_s3,
    generate_s3_uuid,
    get_audio_upload_s3_key,
    download_file_from_s3_as_bytes,
)
from components.badge import create_badge
from lib.init import init_env_vars, init_db
from lib.chat import MessageHistory
from auth import get_logged_in_user
from components.code import (
    get_code_for_ai_feedback,
    retain_code,
    show_code_editor,
    toggle_show_code_output,
)
from lib.audio import validate_audio_input, prepare_audio_input_for_ai
from components.badge import (
    show_badge_dialog,
    show_multiple_badges_dialog,
    check_for_badges_unlocked,
)
from views.task import display_milestone_tasks_in_sidebar, show_task_name

init_env_vars()
init_db()

# set_verbose(True)
# set_debug(True)

st.markdown(
    """
<style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
</style>
""",
    unsafe_allow_html=True,
)


if "email" not in st.query_params:
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")

if "cohort" not in st.query_params:
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")

if "course" not in st.query_params:
    st.error("Not authorized. Redirecting to home page...")
    time.sleep(2)
    st.switch_page("./home.py")

cohort_id = int(st.query_params["cohort"])
cohort = get_cohort_by_id(cohort_id)

login_or_signup_user(st.query_params["email"])

task_id = st.query_params.get("id")

if not task_id:
    st.error("No task id provided")
    st.stop()

try:
    task_index = int(task_id)
except ValueError:
    st.error("Task index must be an integer")
    st.stop()

task = get_task_by_id(task_id)

if not task:
    st.error("No task found")
    st.stop()

if not task["verified"]:
    st.error(
        "Task not verified. Please ask your mentor/teacher to verify the task so that you can solve it."
    )
    st.stop()

st.session_state.scoring_criteria = None
if task["response_type"] == "report":
    st.session_state.scoring_criteria = get_scoring_criteria_for_task(task_id)

if "user" not in st.session_state:
    st.session_state.user = get_logged_in_user()

if "learner" in st.query_params:
    task_user_id = st.query_params["learner"]
else:
    task_user_id = st.session_state.user["id"]

if "mode" in st.query_params and st.query_params["mode"] == "review":
    st.session_state.is_review_mode = True
else:
    st.session_state.is_review_mode = False

if (
    not st.session_state.is_review_mode
    and task["milestone_name"] != uncategorized_milestone_name
):
    course_id = int(st.query_params["course"])
    display_milestone_tasks_in_sidebar(task_user_id, course_id, cohort_id, task)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = get_task_chat_history_for_user(
        task_id, task_user_id
    )

    if task["type"] == "audio":
        with st.spinner("Loading..."):
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    message["data"] = download_file_from_s3_as_bytes(
                        get_audio_upload_s3_key(message["content"])
                    )

if "is_solved" not in st.session_state:
    st.session_state.is_solved = (
        len(st.session_state.chat_history)
        and st.session_state.chat_history[-2]["is_solved"]
    )

if "displayed_attempt_index" not in st.session_state:
    reset_displayed_attempt_index()

if "current_num_attempts" not in st.session_state:
    reset_current_num_attempts()


def reset_ai_running():
    st.session_state.is_ai_running = False


if "is_ai_running" not in st.session_state:
    reset_ai_running()


def reset_ai_chat_history_for_report_tasks():
    # for ai chat history for report type tasks, only keep the first
    # message containing the task details for each run
    initial_ai_chat_history = [st.session_state.ai_chat_history.messages[0]]
    st.session_state.ai_chat_history.clear()
    st.session_state.ai_chat_history.add_messages(initial_ai_chat_history)


def refresh_streak():
    st.session_state.user_streak = get_user_streak(task_user_id, cohort_id)


refresh_streak()

if "audio_file_uploader_key" not in st.session_state:
    st.session_state.audio_file_uploader_key = 0


def update_audio_file_uploader_key():
    st.session_state.audio_file_uploader_key += 1


if "badges_to_show" not in st.session_state:
    st.session_state.badges_to_show = []

if st.session_state.badges_to_show:
    if len(st.session_state.badges_to_show) == 1:
        show_badge_dialog(
            st.session_state.badges_to_show[0], cohort["name"], task["org_name"]
        )
    else:
        show_multiple_badges_dialog(
            st.session_state.badges_to_show, cohort["name"], task["org_name"]
        )
    st.session_state.badges_to_show = []

task_name_container_background_color = None
task_name_container_text_color = None
if st.session_state.is_solved:
    task_name_container_background_color = "#62B670"
    task_name_container_text_color = "white"

back_to_home_button()

show_task_name(
    task,
    task_name_container_background_color,
    task_name_container_text_color,
    st.session_state.is_solved,
)

if task["response_type"] == "chat":
    containers = get_chat_containers(task, st.session_state.is_review_mode)
    if task["type"] == "coding" and not st.session_state.is_review_mode:
        (
            description_container,
            chat_container,
            chat_input_container,
            code_editor_container,
        ) = containers
    else:
        description_container, chat_container, chat_input_container = containers
else:
    (
        navigation_container,
        description_container,
        user_input_display_container,
        ai_report_container,
    ) = get_report_containers()


with description_container:
    st.markdown(task["description"].replace("\n", "\n\n"))


def identify_and_show_unlocked_badges():
    badges_to_show = check_for_badges_unlocked(
        task_user_id, st.session_state.user_streak
    )
    if not badges_to_show:
        return

    st.session_state.badges_to_show = badges_to_show


def transform_user_message_for_ai_history(message: dict):
    return f"""Student's response:\n```\n{message['content']}\n```"""


if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = MessageHistory()

    task_details = f"""Task:\n```\n{task['description']}\n```"""

    if task["response_type"] == "chat":
        task_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{task['answer']}\n```"""

    st.session_state.ai_chat_history.add_user_message(task_details)

    # do not include history for report type tasks
    if task["response_type"] == "chat" and task["type"] != "audio":
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.session_state.ai_chat_history.add_user_message(
                    transform_user_message_for_ai_history(message)
                )
            else:
                st.session_state.ai_chat_history.add_ai_message(message["content"])


if not st.session_state.chat_history:
    empty_container = None
    if task["response_type"] == "chat":
        if st.session_state.is_review_mode:
            chat_container.warning("No task history found")
        else:
            empty_container = chat_container.empty()
            with empty_container:
                st.warning("Your task history will appear here!")
    else:
        if st.session_state.is_review_mode:
            user_input_display_container.warning("No task history found")
        else:
            with user_input_display_container:
                st.warning("Your response will appear here!")
else:
    if task["response_type"] == "chat":
        # Display chat messages from history on app rerun
        for index, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                # import ipdb; ipdb.set_trace()
                display_user_chat_message(chat_container, message["content"])
            else:
                with chat_container.chat_message(message["role"]):
                    ai_message = cleanup_ai_response(message["content"])

                    st.markdown(ai_message, unsafe_allow_html=True)
    else:
        st.session_state.current_num_attempts = len(st.session_state.chat_history) // 2

        set_display_for_restoring_history()

        if st.session_state.current_num_attempts > 1:
            show_attempt_picker(navigation_container)

        displayed_user_message_index = (
            st.session_state.displayed_attempt_index - 1
        ) * 2

        if task["type"] == "text":
            display_user_text_input_report(
                user_input_display_container,
                st.session_state.chat_history[displayed_user_message_index]["content"],
            )
        else:
            display_user_audio_input_report(
                user_input_display_container,
                st.session_state.chat_history[displayed_user_message_index]["data"],
            )

        show_ai_report(
            json.loads(
                st.session_state.chat_history[displayed_user_message_index + 1][
                    "content"
                ]
            ),
            ["Category", "Feedback", "Score"],
            ai_report_container,
        )


def get_ai_feedback_chat(user_response: str, input_type: Literal["text", "code"]):
    # import ipdb; ipdb.set_trace()
    if not st.session_state.chat_history:
        empty_container.empty()

    display_user_chat_message(chat_container, user_response)

    user_message = {"role": "user", "content": user_response}
    st.session_state.chat_history.append(user_message)

    st.session_state.ai_chat_history.add_user_message(
        transform_user_message_for_ai_history(user_message)
    )

    # ipdb.set_trace()
    ai_response, result_dict = get_ai_chat_response(
        st.session_state.ai_chat_history.messages,
        chat_container,
    )

    is_solved = (
        result_dict["is_correct"] if result_dict["is_correct"] is not None else False
    )

    if not st.session_state.is_solved and is_solved:
        st.balloons()
        st.session_state.is_solved = True
        time.sleep(2)

    identify_and_show_unlocked_badges()
    refresh_streak()

    st.session_state.ai_chat_history.add_ai_message(ai_response)

    logger.info(get_formatted_history(st.session_state.ai_chat_history.messages))

    # Add user message to chat history [store to db only if ai response has been completely fetched]
    new_user_message = store_message_to_db(
        task_user_id,
        task_id,
        "user",
        user_response,
        st.session_state.is_solved,
        input_type,
    )
    st.session_state.chat_history[-1] = new_user_message

    # Add assistant response to chat history
    new_ai_message = store_message_to_db(
        task_user_id,
        task_id,
        "assistant",
        ai_response,
        st.session_state.is_solved,
    )
    st.session_state.chat_history.append(new_ai_message)

    # retain_code()
    reset_ai_running()
    st.rerun()


def get_ai_feedback_report_text_input(user_response: str):
    increase_current_num_attempts()
    set_display_for_new_attempt()
    # if st.session_state.current_num_attempts == 2:
    navigation_container.empty()
    # show_attempt_picker(navigation_container)

    display_user_text_input_report(user_input_display_container, user_response)

    user_message = {"role": "user", "content": user_response}
    st.session_state.chat_history.append(user_message)

    st.session_state.ai_chat_history.add_user_message(
        transform_user_message_for_ai_history(user_message)
    )

    rows = get_ai_report_response(
        st.session_state.ai_chat_history.messages,
        st.session_state.scoring_criteria,
        ai_report_container,
        task["type"],
    )

    is_solved = all(
        row[2] == st.session_state.scoring_criteria[index]["range"][1]
        for index, row in enumerate(rows)
    )

    if not st.session_state.is_solved and is_solved:
        st.balloons()
        st.session_state.is_solved = True
        time.sleep(2)

    ai_response = json.dumps(rows)

    identify_and_show_unlocked_badges()
    refresh_streak()

    # st.session_state.ai_chat_history.add_ai_message(ai_response)

    logger.info(get_formatted_history(st.session_state.ai_chat_history.messages))

    # Add user message to chat history [store to db only if ai response has been completely fetched]
    new_user_message = store_message_to_db(
        task_user_id,
        task_id,
        "user",
        user_response,
        st.session_state.is_solved,
        "text",
    )
    st.session_state.chat_history[-1] = new_user_message

    # Add assistant response to chat history
    new_ai_message = store_message_to_db(
        task_user_id,
        task_id,
        "assistant",
        ai_response,
        st.session_state.is_solved,
    )
    st.session_state.chat_history.append(new_ai_message)

    # for ai chat history for report type tasks, only keep the first
    # message containing the task details for each run
    reset_ai_chat_history_for_report_tasks()

    reset_ai_running()
    st.rerun()


def get_ai_feedback_report_audio_input(audio_data: bytes):
    update_audio_file_uploader_key()

    increase_current_num_attempts()
    set_display_for_new_attempt()
    navigation_container.empty()

    display_user_audio_input_report(user_input_display_container, audio_data)

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "input_audio",
                "input_audio": {
                    "data": prepare_audio_input_for_ai(audio_data),
                    "format": "wav",
                },
            },
        ],
    }
    st.session_state.chat_history.append(user_message)

    st.session_state.ai_chat_history.add_messages([user_message])

    rows = get_ai_report_response(
        st.session_state.ai_chat_history.messages,
        st.session_state.scoring_criteria,
        ai_report_container,
        task["type"],
    )

    is_solved = all(
        row[2] == st.session_state.scoring_criteria[index]["range"][1]
        for index, row in enumerate(rows)
    )

    if not st.session_state.is_solved and is_solved:
        st.balloons()
        st.session_state.is_solved = True
        time.sleep(2)

    ai_response = json.dumps(rows)

    identify_and_show_unlocked_badges()
    refresh_streak()

    # upload audio to s3
    uuid = generate_s3_uuid()
    s3_key = get_audio_upload_s3_key(uuid)
    upload_audio_data_to_s3(
        audio_data,
        s3_key,
    )

    # logger.info(get_formatted_history(st.session_state.ai_chat_history.messages))

    # Add user message to chat history [store to db only if ai response has been completely fetched]
    new_user_message = store_message_to_db(
        task_user_id,
        task_id,
        "user",
        uuid,
        st.session_state.is_solved,
        "audio",
    )
    # store the raw audio bytes as cache
    # later, only pull from s3 if `data` is not present in the message
    new_user_message["data"] = audio_data
    st.session_state.chat_history[-1] = new_user_message

    # Add assistant response to chat history
    new_ai_message = store_message_to_db(
        task_user_id,
        task_id,
        "assistant",
        ai_response,
        st.session_state.is_solved,
    )
    st.session_state.chat_history.append(new_ai_message)

    reset_ai_chat_history_for_report_tasks()

    reset_ai_running()
    st.rerun()


def get_ai_feedback_on_code():
    toggle_show_code_output()
    get_ai_feedback_chat(get_code_for_ai_feedback(), "code")


if "show_code_output" not in st.session_state:
    st.session_state.show_code_output = False


def set_ai_running():
    st.session_state.is_ai_running = True
    retain_code()


if task["type"] == "coding" and not st.session_state.is_review_mode:
    show_code_editor(
        task, code_editor_container, set_ai_running, get_ai_feedback_on_code
    )

user_response_placeholder = "Your response"

if task["type"] == "coding":
    user_response_placeholder = (
        "Use the code editor for submitting code and ask/tell anything else here"
    )
else:
    user_response_placeholder = "Write your response here"


def show_and_handle_chat_input():
    if st.session_state.is_review_mode:
        return

    if user_response := st.chat_input(
        user_response_placeholder,
        key="chat_input",
        on_submit=set_ai_running,
        disabled=st.session_state.is_ai_running,
    ):
        get_ai_feedback_chat(user_response, "text")


def show_and_handle_report_input():
    if st.session_state.is_review_mode:
        return

    if task["type"] == "text":
        if user_response := st.chat_input(
            user_response_placeholder,
            key="report_input",
            on_submit=set_ai_running,
            disabled=st.session_state.is_ai_running,
        ):
            get_ai_feedback_report_text_input(user_response)
    elif task["type"] == "audio":
        audio_value = st.audio_input(
            "Record a voice message by pressing on the mic icon",
            disabled=st.session_state.is_ai_running,
            on_change=set_ai_running,
            key=f"audio_input_{st.session_state.audio_file_uploader_key}",
        )
        if audio_value:
            if not validate_audio_input(audio_value):
                reset_ai_running()
                st.stop()

            audio_data = audio_value.read()
            get_ai_feedback_report_audio_input(audio_data)
    else:
        raise NotImplementedError(f"Task type {task['type']} not supported")


if task["response_type"] == "chat":
    if chat_input_container:
        with chat_input_container:
            show_and_handle_chat_input()
    else:
        show_and_handle_chat_input()
else:
    show_and_handle_report_input()
