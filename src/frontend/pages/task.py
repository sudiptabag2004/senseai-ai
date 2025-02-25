from typing import List, Literal
import os
import time
import traceback
import requests
import json
from copy import deepcopy

import streamlit as st

st.set_page_config(
    page_title="Task | SensAI", layout="wide", initial_sidebar_state="collapsed"
)

from lib.init import init_app

init_app()

from lib.llm import get_formatted_history
from lib.organization import get_org_by_id
from lib.utils.logging import logger
from components.buttons import back_to_home_button, link_button
from auth import login_or_signup_user, unauthorized_redirect_to_home
from lib.config import uncategorized_milestone_name
from lib.chat_history import (
    get_task_chat_history_for_user,
    store_message as store_message_to_db,
)
from lib.user import get_user_streak, is_user_in_cohort
from lib.task import get_task, get_scoring_criteria_for_task
from lib.cohort import get_cohort_by_id
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
from lib.output_formats.reading import (
    get_containers as get_reading_containers,
)

from lib.ui import (
    cleanup_ai_response,
)
from lib.utils.encryption import decrypt_openai_api_key, encrypt_openai_api_key
from lib.s3 import (
    upload_audio_data_to_s3,
    generate_s3_uuid,
    get_audio_upload_s3_key,
    download_file_from_s3_as_bytes,
)
from lib.chat import MessageHistory
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
from components.milestone_learner_view import get_task_url
from views.task import display_milestone_tasks_in_sidebar, show_task_name
from lib.toast import show_toast, set_toast

# set_verbose(True)
# set_debug(True)

show_toast()

st.markdown(
    """
<style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.stChatInput) {
            height: 60px !important;
        }
</style>
""",
    unsafe_allow_html=True,
)

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

st.session_state.org = get_org_by_id(cohort["org_id"])

course_id = int(st.query_params["course"])

login_or_signup_user()

if not is_user_in_cohort(st.session_state.user["id"], cohort_id):
    unauthorized_redirect_to_home()

task_id = st.query_params.get("id")

if not task_id:
    st.error("No task id provided")
    st.stop()

try:
    task_id = int(task_id)
except ValueError:
    st.error("Task index must be an integer")
    st.stop()

task = get_task(task_id, course_id)


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

    if not st.session_state.scoring_criteria:
        st.error(
            "No scoring criteria found for this task. Please contact your admin to set up scoring criteria for this task!"
        )
        st.stop()

if "learner" in st.query_params:
    task_user_id = st.query_params["learner"]
else:
    task_user_id = st.session_state.user["id"]

if "mode" in st.query_params and st.query_params["mode"] == "review":
    st.session_state.is_review_mode = True
else:
    st.session_state.is_review_mode = False

prev_task, next_task = None, None
if (
    not st.session_state.is_review_mode
    and task["milestone_name"] != uncategorized_milestone_name
):
    prev_task, next_task = display_milestone_tasks_in_sidebar(
        task_user_id, course_id, cohort_id, task
    )

if "chat_history" not in st.session_state:
    st.session_state.chat_history = get_task_chat_history_for_user(
        task_id, task_user_id
    )

    if task["input_type"] == "audio":
        with st.spinner("Loading..."):
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    message["data"] = download_file_from_s3_as_bytes(
                        get_audio_upload_s3_key(message["content"])
                    )

if "is_solved" not in st.session_state:
    last_user_message_index = -1 if task["type"] == "reading_material" else -2
    st.session_state.is_solved = (
        len(st.session_state.chat_history)
        and st.session_state.chat_history[last_user_message_index]["is_solved"]
    )

if "displayed_attempt_index" not in st.session_state:
    reset_displayed_attempt_index()

if "current_num_attempts" not in st.session_state:
    reset_current_num_attempts()


def reset_ai_running():
    st.session_state.is_ai_running = False


if "is_ai_running" not in st.session_state:
    reset_ai_running()


def reset_ai_chat_history():
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
            st.session_state.badges_to_show[0],
        )
    else:
        show_multiple_badges_dialog(
            st.session_state.badges_to_show,
        )
    st.session_state.badges_to_show = []

task_name_container_background_color = None
task_name_container_text_color = None
if st.session_state.is_solved:
    task_name_container_background_color = "#62B670"
    task_name_container_text_color = "white"


def mark_as_read():
    st.balloons()
    st.session_state.is_solved = True
    time.sleep(2)

    store_message_to_db(
        task_user_id,
        task_id,
        "user",
        None,
        st.session_state.is_solved,
        None,
    )


if task["type"] == "reading_material":
    button_text = "✅ Marked as Read" if st.session_state.is_solved else "Mark as Read"
    st.button(
        button_text,
        on_click=mark_as_read,
        type="primary",
        disabled=st.session_state.is_solved,
    )

header_cols = st.columns([1, 7])
with header_cols[0]:
    back_to_home_button(
        params={
            "org_id": cohort["org_id"],
            "cohort_id": cohort_id,
            "course_id": course_id,
        }
    )

with header_cols[1]:
    show_task_name(
        task,
        task_name_container_background_color,
        task_name_container_text_color,
        st.session_state.is_solved,
    )


if task["type"] == "question":
    if task["response_type"] in ["chat", "exam"]:
        containers = get_chat_containers(task, st.session_state.is_review_mode)
        if task["input_type"] == "coding" and not st.session_state.is_review_mode:
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
            chat_input_container,
        ) = get_report_containers(st.session_state.is_review_mode, task["input_type"])

else:
    user_input_display_container = None
    description_container = get_reading_containers()


with description_container:
    st.markdown(task["description"].replace("\n", "\n\n"))


def identify_and_show_unlocked_badges():
    badges_to_show = check_for_badges_unlocked(
        task_user_id, st.session_state.user_streak, cohort_id
    )
    if not badges_to_show:
        return

    st.session_state.badges_to_show = badges_to_show


def transform_user_message_for_ai_history(message: dict):
    return f"""Student's response:\n```\n{message['content']}\n```"""


if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = MessageHistory()

    task_details = f"""Task:\n```\n{task['description']}\n```"""

    if task["response_type"] in ["chat", "exam"]:
        task_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{task['answer']}\n```"""

    st.session_state.ai_chat_history.add_user_message(task_details)

    # do not include history for report or exam type tasks
    if task["response_type"] in ["chat"]:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.session_state.ai_chat_history.add_user_message(
                    transform_user_message_for_ai_history(message)
                )
            else:
                st.session_state.ai_chat_history.add_ai_message(message["content"])

if task["type"] == "question":
    if not st.session_state.chat_history:
        empty_container = None
        if task["response_type"] in ["chat", "exam"]:
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
        if task["response_type"] in ["chat", "exam"]:
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
            st.session_state.current_num_attempts = (
                len(st.session_state.chat_history) // 2
            )

            set_display_for_restoring_history()

            if st.session_state.current_num_attempts > 1:
                show_attempt_picker(navigation_container)

            displayed_user_message_index = (
                st.session_state.displayed_attempt_index - 1
            ) * 2

            if task["input_type"] == "text":
                display_user_text_input_report(
                    user_input_display_container,
                    st.session_state.chat_history[displayed_user_message_index][
                        "content"
                    ],
                    st.session_state.is_review_mode,
                )
            else:
                if (
                    "data"
                    not in st.session_state.chat_history[displayed_user_message_index]
                ):
                    st.session_state.chat_history[displayed_user_message_index][
                        "data"
                    ] = download_file_from_s3_as_bytes(
                        get_audio_upload_s3_key(
                            st.session_state.chat_history[displayed_user_message_index][
                                "content"
                            ]
                        )
                    )

                display_user_audio_input_report(
                    user_input_display_container,
                    st.session_state.chat_history[displayed_user_message_index]["data"],
                    st.session_state.is_review_mode,
                )

            with ai_report_container:
                show_ai_report(
                    json.loads(
                        st.session_state.chat_history[displayed_user_message_index + 1][
                            "content"
                        ]
                    ),
                    ["Category", "Feedback", "Score"],
                )


def get_ai_feedback_chat(
    user_response: str,
    input_type: Literal["text", "code"],
):
    # import ipdb; ipdb.set_trace()
    if not st.session_state.chat_history:
        empty_container.empty()

    display_user_chat_message(chat_container, user_response)

    user_message = {"role": "user", "content": user_response}
    st.session_state.chat_history.append(user_message)

    st.session_state.ai_chat_history.add_user_message(
        transform_user_message_for_ai_history(user_message)
    )

    with chat_container.chat_message("assistant"):
        ai_response_container = st.empty()

    # ipdb.set_trace()
    with ai_response_container:
        try:
            ai_response, result_dict = get_ai_chat_response(
                st.session_state.ai_chat_history.messages,
                task["response_type"],
                task["context"],
                decrypt_openai_api_key(st.session_state.org["openai_api_key"]),
                st.session_state.org["openai_free_trial"],
            )
        except Exception:
            traceback.print_exc()
            st.markdown(
                "<p style='color: red;'>Error fetching AI feedback. Please reload the page and try again.</p>",
                unsafe_allow_html=True,
            )

            return

    is_solved = (
        result_dict["is_correct"] if result_dict["is_correct"] is not None else False
    )

    if task["response_type"] == "exam":
        if is_solved:
            ai_response = "✅ Your response is correct!"
        else:
            ai_response = "Not quite right. Try again!"

    if not st.session_state.is_solved and is_solved:
        st.balloons()
        st.session_state.is_solved = True
        time.sleep(2)

    if task["response_type"] == "exam":
        reset_ai_chat_history()
    else:
        st.session_state.ai_chat_history.add_ai_message(ai_response)

    identify_and_show_unlocked_badges()
    refresh_streak()

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

    with ai_report_container:
        try:
            rows = get_ai_report_response(
                st.session_state.ai_chat_history.messages,
                st.session_state.scoring_criteria,
                task["context"],
                task["input_type"],
                decrypt_openai_api_key(st.session_state.org["openai_api_key"]),
                st.session_state.org["openai_free_trial"],
            )
        except:
            st.markdown(
                "<p style='color: red;'>Error fetching AI feedback. Please reload the page and try again.</p>",
                unsafe_allow_html=True,
            )

            return

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
    reset_ai_chat_history()

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

    with ai_report_container:
        try:
            rows = get_ai_report_response(
                st.session_state.ai_chat_history.messages,
                st.session_state.scoring_criteria,
                task["context"],
                task["input_type"],
                decrypt_openai_api_key(st.session_state.org["openai_api_key"]),
                st.session_state.org["openai_free_trial"],
            )
        except:
            st.markdown(
                "<p style='color: red;'>Error fetching AI feedback. Please reload the page and try again.</p>",
                unsafe_allow_html=True,
            )

            return

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

    reset_ai_chat_history()

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


if task["input_type"] == "coding" and not st.session_state.is_review_mode:
    show_code_editor(
        task, code_editor_container, set_ai_running, get_ai_feedback_on_code
    )

user_response_placeholder = "Your response"

if task["input_type"] == "coding":
    user_response_placeholder = (
        "Use the code editor for submitting code and ask/tell anything else here"
    )
else:
    user_response_placeholder = "Write your response here"


def show_and_handle_chat_input():
    if st.session_state.is_review_mode:
        return

    is_disabled = st.session_state.is_ai_running

    if task["response_type"] == "exam":
        is_disabled = is_disabled or st.session_state.is_solved

    if user_response := st.chat_input(
        user_response_placeholder,
        key="chat_input",
        on_submit=set_ai_running,
        disabled=is_disabled,
    ):
        get_ai_feedback_chat(user_response, "text")


def show_and_handle_report_input():
    if st.session_state.is_review_mode:
        return

    if task["input_type"] == "text":
        if user_response := st.chat_input(
            user_response_placeholder,
            key="report_input",
            on_submit=set_ai_running,
            disabled=st.session_state.is_ai_running,
        ):
            get_ai_feedback_report_text_input(user_response)
    elif task["input_type"] == "audio":
        audio_value = st.audio_input(
            "Record a voice message by pressing on the mic icon",
            disabled=st.session_state.is_ai_running,
            on_change=set_ai_running,
            key=f"audio_input_{st.session_state.audio_file_uploader_key}",
        )
        if audio_value:
            error = validate_audio_input(audio_value)
            if error:
                set_toast(error, "🚫")
                reset_ai_running()
                update_audio_file_uploader_key()
                st.rerun()

            audio_data = audio_value.read()
            get_ai_feedback_report_audio_input(audio_data)
    else:
        raise NotImplementedError(f"Task type {task['input_type']} not supported")


if task["type"] == "question":
    with chat_input_container:
        if task["response_type"] in ["chat", "exam"]:
            show_and_handle_chat_input()
        else:
            show_and_handle_report_input()


nav_cols = st.columns([1, 2, 1])


def truncate_task_name(task_name: str):
    return task_name[:27] + "..." if len(task_name) > 30 else task_name


if prev_task is not None:
    prev_task_url = get_task_url(prev_task, cohort_id, course_id)
    with nav_cols[0]:
        link_button(
            f"{truncate_task_name(prev_task['name'])}",
            prev_task_url,
            icon="←",
            icon_position="left",
        )

if next_task is not None:
    next_task_url = get_task_url(next_task, cohort_id, course_id)
    with nav_cols[-1]:
        link_button(
            f"{truncate_task_name(next_task['name'])}",
            next_task_url,
            icon="→",
            icon_position="right",
        )
