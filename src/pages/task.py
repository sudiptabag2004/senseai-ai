from typing import List, Literal
from typing_extensions import TypedDict, Annotated
import os
import time
import json
from functools import partial
import html
from pydantic import BaseModel, Field
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import JsonOutputParser
import re

from langchain.globals import set_verbose, set_debug
from langchain_core.messages import HumanMessage, AIMessage

import streamlit as st

st.set_page_config(
    page_title="Task | SensAI", layout="wide", initial_sidebar_state="collapsed"
)

from streamlit_ace import st_ace, THEMES

from lib.llm import logger, get_formatted_history
from components.sticky_container import sticky_container
from components.buttons import back_to_home_button
from auth import login_or_signup_user
from lib.config import coding_languages_supported, uncategorized_milestone_name
from lib.db import (
    get_task_by_id,
    store_message as store_message_to_db,
    get_task_chat_history_for_user,
    delete_message as delete_message_from_db,
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
)
from lib.ui import (
    display_waiting_indicator,
    escape_text_outside_code_blocks,
    correct_newlines_outside_code_blocks,
    correct_code_blocks,
)
from components.badge import create_badge
from lib.init import init_env_vars, init_db
from lib.chat import MessageHistory
from lib.utils import get_current_time_in_ist
from auth import get_logged_in_user
from components.code_execution import (
    execute_code,
    run_tests,
    react_default_code,
    show_react_help_text,
    sql_default_code,
    show_sql_help_text,
)
from components.badge import show_badge_dialog, show_multiple_badges_dialog
from components.milestone_learner_view import get_task_url
from views.roadmap import get_tasks_with_completion_status

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
    course_tasks = get_tasks_with_completion_status(
        task_user_id, cohort_id, course_id, task["milestone_id"]
    )

    with st.sidebar.container(border=True):
        st.subheader(task["milestone_name"])

    for index, course_task in enumerate(course_tasks):
        # with st.sidebar:
        #     set_task_view_style()
        #     st.markdown(
        #         get_task_view(course_task, cohort_id, course_id, show_button=False),
        #         unsafe_allow_html=True,
        #     )
        course_text_to_display = course_task["name"].strip()

        if course_task["completed"]:
            course_text_to_display = "✅ " + course_text_to_display

        task_url = get_task_url(course_task, cohort_id, course_id)

        if course_task["id"] == int(task_id):
            st.sidebar.markdown(
                f"""<div style='background-color: #ADADB2; padding: 8px 12px; border-radius: 0.5rem; margin: 0 0 16px 0;'>{course_text_to_display}</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                f'<a href="{task_url}" target="_self" style="text-decoration: none; background-color: #dfe3eb; padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">{course_text_to_display}</a>',
                unsafe_allow_html=True,
            )
            # st.sidebar.link_button(course_text_to_display, task_url, **kwargs)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = get_task_chat_history_for_user(
        task_id, task_user_id
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


def refresh_streak():
    st.session_state.user_streak = get_user_streak(task_user_id, cohort_id)


refresh_streak()

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

with sticky_container(
    border=True,
    background_color=task_name_container_background_color,
    text_color=task_name_container_text_color,
):
    # st.link_button('Open task list', '/task_list')

    heading = f"**{task['name'].strip()}**"
    if st.session_state.is_solved:
        heading += " ✅"
    st.write(heading)

    # st.container(height=10, border=False)


# st.session_state
# st.session_state['code']

if task["response_type"] == "chat":
    if task["type"] == "coding" and not st.session_state.is_review_mode:
        chat_column, code_column = st.columns(2)
        description_container = chat_column.container(height=200)
        chat_container = chat_column.container(height=325)

        code_input_container = code_column.container(height=475, border=False)
        chat_input_container = code_column.container(height=100, border=False)
    else:
        # chat_column = st.columns(1)[0]
        description_col, chat_col = st.columns(2)

        description_container = description_col.container(height=450, border=True)
        chat_container = chat_col.container(border=True, height=450)

        chat_input_container = None
else:
    input_description_col, _, report_col = st.columns([1, 0.1, 1.5])
    description_container = input_description_col.container(height=450, border=True)

    navigation_container = report_col.container().empty()
    user_input_display_container = report_col.container(
        height=100, border=False
    ).empty()
    report_col.container(height=1, border=False)
    report_height = 300 if st.session_state.current_num_attempts > 1 else 250
    ai_report_container = report_col.container(
        border=False, height=report_height
    ).empty()


with description_container:
    st.markdown(task["description"].replace("\n", "\n\n"))


def transform_user_message_for_ai_history(message: dict):
    return f"""Student's response:\n```\n{message['content']}\n```"""


def transform_assistant_message_for_ai_history(message: dict):
    # return {"role": message['role'], "content": message['content']}
    return message["content"]


if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = MessageHistory()

    task_details = f"""Task:\n```\n{task['description']}\n```"""

    if task["response_type"] == "chat":
        task_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{task['answer']}\n```"""

    st.session_state.ai_chat_history.add_user_message(task_details)

    for message in st.session_state.chat_history:
        # import ipdb; ipdb.set_trace()
        if message["role"] == "user":
            # import ipdb; ipdb.set_trace()
            st.session_state.ai_chat_history.add_user_message(
                transform_user_message_for_ai_history(message)
            )
        else:
            st.session_state.ai_chat_history.add_ai_message(
                transform_assistant_message_for_ai_history(message)
            )

# st.session_state.ai_chat_history
# st.session_state.chat_history

# st.stop()


def delete_user_chat_message(index_to_delete: int):
    # delete both the user message and the AI assistant's response to it
    updated_chat_history = st.session_state.chat_history[:index_to_delete]
    current_ai_chat_history = st.session_state.ai_chat_history.messages
    # import ipdb; ipdb.set_trace()
    ai_chat_index_to_delete = (
        index_to_delete + 1
    )  # since we have an extra message in ai_chat_history at the start
    updated_ai_chat_history = current_ai_chat_history[:ai_chat_index_to_delete]

    delete_message_from_db(
        st.session_state.chat_history[index_to_delete]["id"]
    )  # delete user message
    delete_message_from_db(
        st.session_state.chat_history[index_to_delete + 1]["id"]
    )  # delete ai message

    if index_to_delete + 2 < len(st.session_state.chat_history):
        updated_chat_history += st.session_state.chat_history[index_to_delete + 2 :]
        updated_ai_chat_history += current_ai_chat_history[
            ai_chat_index_to_delete + 2 :
        ]

    st.session_state.chat_history = updated_chat_history
    st.session_state.ai_chat_history.clear()
    st.session_state.ai_chat_history.add_messages(updated_ai_chat_history)

    refresh_streak()


def display_user_chat_message(user_response: str, message_index: int):
    # delete_button_key = f"message_{message_index}"
    # if delete_button_key in st.session_state:
    #     return

    with chat_container.chat_message("user"):
        # user_answer_cols = st.columns([5, 1])
        st.markdown(user_response, unsafe_allow_html=True)
        if st.session_state.is_review_mode:
            return

        # user_answer_cols[1].button(
        #     "Delete",
        #     on_click=partial(delete_user_chat_message, index_to_delete=message_index),
        #     key=delete_button_key,
        #     disabled=st.session_state.is_ai_running,
        # )


def display_user_input_report(user_response: str):
    # delete_button_key = f"message_{message_index}"
    # if delete_button_key in st.session_state:
    #     return

    with user_input_display_container:
        # user_answer_cols = st.columns([5, 1])
        st.markdown(f"**Your response**<br>{user_response}", unsafe_allow_html=True)
        if st.session_state.is_review_mode:
            return

        # user_answer_cols[1].button(
        #     "Delete",
        #     on_click=partial(delete_user_chat_message, index_to_delete=message_index),
        #     key=delete_button_key,
        #     disabled=st.session_state.is_ai_running,
        # )


# st.session_state.chat_history
# st.session_state.ai_chat_history

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
        # TODO: add this for report type
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
                display_user_chat_message(message["content"], message_index=index)
            else:
                with chat_container.chat_message(message["role"]):
                    ai_message = escape_text_outside_code_blocks(
                        correct_code_blocks(message["content"])
                    )

                    # ai is supposed to return all html tags within backticks, but in case it doesn't
                    # html.escape will escape the html tags; but this will mess up the html tags that
                    # were returned within backticks; so, we fix those html tags that would have been
                    # incorrectly escaped as well.
                    ai_message = ai_message.replace("`&lt;", "`<")
                    ai_message = ai_message.replace("&gt;`", ">`")

                    st.markdown(ai_message, unsafe_allow_html=True)
    else:
        st.session_state.current_num_attempts = len(st.session_state.chat_history) // 2

        set_display_for_restoring_history()

        if st.session_state.current_num_attempts > 1:
            show_attempt_picker(navigation_container)

        displayed_user_message_index = (
            st.session_state.displayed_attempt_index - 1
        ) * 2

        display_user_input_report(
            st.session_state.chat_history[displayed_user_message_index]["content"]
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


def get_session_history():
    return st.session_state.ai_chat_history


def get_ai_chat_response(user_message: str):
    import instructor
    import openai

    client = instructor.from_openai(openai.OpenAI())

    # class Output(TypedDict):
    #     response: Annotated[str, "Your response to the student's message"]
    #     is_solved: Annotated[bool, "Whether the student's response correctly solves the task"]

    class Output(BaseModel):
        feedback: List[str] = Field(
            description="Feedback on the student's response; return each word as a separate element in the list; add newline characters to the feedback to make it more readable"
        )
        is_correct: bool = Field(
            description="Whether the student's response correctly solves the task given to the student"
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    # print(format_instructions)

    system_prompt = f"""You are a Socratic tutor.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nUse the following principles for responding to the student:\n- Ask thought-provoking, open-ended questions that challenges the student's preconceptions and encourage them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n- Avoid giving feedback using the same words in subsequent messages because that makes the feedback monotonic. Maintain diversity in your feedback and always keep the tone welcoming.\n- If the student's response is not relevant to the task, remain curious and empathetic while playfully nudging them back to the task in your feedback.\n- Include an emoji in every few feedback messages [refer to the history provided to decide if an emoji should be added].\n- If the task resolves around code, use backticks ("`", "```") to format sections of code or variable/function names in your feedback.\n- No matter how frustrated the student gets or how many times they ask you for the answer, you must never give away the entire answer in one go. Always provide them hints to let them discover the answer step by step on their own.\n\nImportant Instructions:\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n- Whenever you include any html in your feedback, make sure that the html tags are enclosed within backticks (i.e. `<html>` instead of <html>).\n\n{format_instructions}"""

    model = "gpt-4o-2024-08-06"

    st.session_state.ai_chat_history.add_user_message(
        transform_user_message_for_ai_history(user_message)
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ] + st.session_state.ai_chat_history.messages

    # import ipdb; ipdb.set_trace()

    return client.chat.completions.create_partial(
        model=model,
        messages=messages,
        response_model=Output,
        stream=True,
        max_completion_tokens=2048,
        top_p=1,
        temperature=0,
        frequency_penalty=0,
        presence_penalty=0,
        store=True,
    )


def check_for_badges_unlocked():
    # scenarios:
    # 1. streak does not exist - nothing to check in this case
    # 2. streak exists and now 1 more day is added to it
    #   a) if the check below does not pass: it means the streak for current day is already accounted for
    #   b) if the check below passes:
    #       i) it makes the current streak equal to the existing current streak badge value (e.g. if user deleted all messages for today and added new messages, then the streak will remain the same). Nothing to do in this case.
    #       ii) it makes the current streak greater than the existing current streak badge value. In this case, we need to update the current streak badge
    #           1. this current streak is the only streak the user ever had, nothing to do in this case
    #           2. this current streak is a new streak with a previously larger streak in history:
    #               a) if there is no longest streak badge, then, create a new longest streak badge with the older streak value
    #               b) if there is a longest streak badge, then, compare the current streak with the longest streak badge value and update the longest streak badge if the current streak is greater than the longest streak badge value and show it as a badge
    if st.session_state.user_streak:
        # if a streak already exists (of one or more days of continuous usage)
        today = get_current_time_in_ist().date()
        streak_last_date = st.session_state.user_streak[0]

        if (today - streak_last_date).days == 1:
            current_streak = len(st.session_state.user_streak) + 1

            streak_badge_id = create_badge(
                task_user_id,
                str(current_streak),
                "streak",
            )

            if streak_badge_id is not None:

                st.session_state.badges_to_show.append(streak_badge_id)

                longest_streak_badge = get_badge_by_type_and_user_id(
                    st.session_state.user["id"], "longest_streak"
                )

                # if no longest streak badge exists, then, the current streak is the first and longest streak
                # no need to do anything in this case
                # but if the longest streak badge exists, then, we need to compare the current streak with the longest streak
                # if the current streak is greater than the longest streak, then, we need to update the longest streak badge
                if longest_streak_badge is not None and current_streak > int(
                    longest_streak_badge["value"]
                ):

                    longest_streak_badge_id = create_badge(
                        task_user_id, str(current_streak), "longest_streak"
                    )
                    st.session_state.badges_to_show.append(longest_streak_badge_id)


def get_ai_feedback_chat(user_response: str, input_type: Literal["text", "code"]):
    # import ipdb; ipdb.set_trace()
    if not st.session_state.chat_history:
        empty_container.empty()

    display_user_chat_message(user_response, len(st.session_state.chat_history))

    user_message = {"role": "user", "content": user_response}
    st.session_state.chat_history.append(user_message)

    # ipdb.set_trace()

    # Display assistant response in chat message container
    with chat_container.chat_message("assistant"):
        ai_response_container = st.empty()

        with ai_response_container:
            display_waiting_indicator()

        for extraction in get_ai_chat_response(user_message):
            if json_dump := extraction.model_dump():
                # print(json_dump)
                ai_response_list = json_dump["feedback"]
                if ai_response_list:
                    ai_response = " ".join(ai_response_list)
                    ai_response = correct_code_blocks(ai_response)
                    ai_response = correct_newlines_outside_code_blocks(ai_response)
                    ai_response_container.markdown(ai_response, unsafe_allow_html=True)

                is_solved = (
                    json_dump["is_correct"]
                    if json_dump["is_correct"] is not None
                    else False
                )

                if not st.session_state.is_solved and is_solved:
                    st.balloons()
                    st.session_state.is_solved = True
                    time.sleep(2)

        # st.write(ai_response)

    check_for_badges_unlocked()
    refresh_streak()

    st.session_state.ai_chat_history.add_ai_message(ai_response)

    logger.info(get_formatted_history(st.session_state.ai_chat_history.messages))

    # st.session_state.chat_history.append(ai_response)
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


def get_ai_feedback_report(user_response: str):
    increase_current_num_attempts()
    set_display_for_new_attempt()

    # if st.session_state.current_num_attempts == 2:
    navigation_container.empty()
    # show_attempt_picker(navigation_container)

    display_user_input_report(user_response)

    user_message = {"role": "user", "content": user_response}
    st.session_state.chat_history.append(user_message)

    st.session_state.ai_chat_history.add_user_message(
        transform_user_message_for_ai_history(user_message)
    )

    rows = get_ai_report_response(
        st.session_state.ai_chat_history.messages,
        st.session_state.scoring_criteria,
        ai_report_container,
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

    check_for_badges_unlocked()
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

    reset_ai_running()
    st.rerun()


# st.session_state.ai_chat_history
# st.session_state.is_solved

supported_language_keys = [
    "html_code",
    "css_code",
    "js_code",
    "nodejs_code",
    "python_code",
    "react_code",
    "sql_code",
]


def retain_code():
    for key in supported_language_keys:
        # avoid checking for st.session_state[key] being not None as it prevents the code
        # from being restored later on when a chat history is restored
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def is_any_code_present():
    return bool(
        st.session_state.get("html_code", "")
        or st.session_state.get("css_code", "")
        or st.session_state.get("js_code", "")
        or st.session_state.get("nodejs_code", "")
        or st.session_state.get("python_code", "")
        or st.session_state.get("react_code", "")
        or st.session_state.get("sql_code", "")
    )


def get_preview_code():
    if not is_any_code_present():
        return ""

    combined_code = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            {css_code}  <!-- Insert the CSS code here -->
        </style>
    </head>
    <body>
        {html_code}  <!-- Insert the HTML code here -->
        <script>
            {js_code}  <!-- Insert the JavaScript code here -->
        </script>
    </body>
    </html>
    """

    return combined_code.format(
        html_code=st.session_state.html_code,
        css_code=st.session_state.css_code,
        js_code=st.session_state.js_code,
    )


def clean_code(code: str):
    return code.strip()


def get_code_for_ai_feedback():
    combined_code = []

    if st.session_state.get("html_code"):
        combined_code.append(f"```html\n{clean_code(st.session_state.html_code)}\n```")

    if st.session_state.get("css_code"):
        combined_code.append(f"```css\n{clean_code(st.session_state.css_code)}\n```")

    if st.session_state.get("js_code"):
        combined_code.append(f"```js\n{clean_code(st.session_state.js_code)}\n```")

    if st.session_state.nodejs_code:
        combined_code.append(f"```js\n{clean_code(st.session_state.nodejs_code)}\n```")

    if st.session_state.python_code:
        combined_code.append(
            f"```python\n{clean_code(st.session_state.python_code)}\n```"
        )
    if st.session_state.react_code:
        combined_code.append(f"```jsx\n{clean_code(st.session_state.react_code)}\n```")
    if st.session_state.sql_code:
        combined_code.append(f"```sql\n{clean_code(st.session_state.sql_code)}\n```")

    # st.session_state.js_code

    # combined_code = combined_code.replace('`', '\`').replace('{', '\{').replace('}', '\}').replace('$', '\$')
    # combined_code = f'`{combined_code}`'
    return "\n\n".join(combined_code)


def get_ai_feedback_on_code():
    toggle_show_code_output()
    get_ai_feedback_chat(get_code_for_ai_feedback(), "code")


if "show_code_output" not in st.session_state:
    st.session_state.show_code_output = False


def toggle_show_code_output():
    # submit_button_col.write(is_any_code_present())
    if not st.session_state.show_code_output and not is_any_code_present():
        return

    st.session_state.show_code_output = not st.session_state.show_code_output
    retain_code()


def set_ai_running():
    st.session_state.is_ai_running = True
    retain_code()


def restore_code_snippets(chat_history):
    code_pattern = re.compile(r"```(\w+)\n([\s\S]*?)```")

    for message in reversed(chat_history):
        if not message.get("response_type") == "code":
            continue

        content = message.get("content", "")
        snippets = code_pattern.findall(content)
        if snippets:
            return {
                f"{language.lower()}_code": code.strip() for language, code in snippets
            }

    return {}


if task["type"] == "coding" and not st.session_state.is_review_mode:
    restored_code_snippets = restore_code_snippets(st.session_state.chat_history)

    for lang, code in restored_code_snippets.items():
        if lang not in st.session_state:
            st.session_state[lang] = code

    if "React" in task["coding_language"] and "react_code" not in st.session_state:
        st.session_state["react_code"] = react_default_code
    if "SQL" in task["coding_language"] and "sql_code" not in st.session_state:
        st.session_state["sql_code"] = sql_default_code

    with code_input_container:
        for lang in supported_language_keys:
            if lang not in st.session_state:
                st.session_state[lang] = ""

        close_preview_button_col, _, _, submit_button_col = st.columns([2, 1, 1, 1])

        # st.session_state.show_code_output

        if not st.session_state.show_code_output:
            lang_name_to_tab_name = {
                "HTML": "HTML",
                "CSS": "CSS",
                "Javascript": "JS",
                "NodeJS": "NodeJS",
                "Python": "Python",
                "React": "React",
                "SQL": "SQL",
            }
            tab_name_to_language = {
                "HTML": "html",
                "CSS": "css",
                "JS": "javascript",
                "NodeJS": "javascript",
                "Python": "python",
                "React": "jsx",
                "SQL": "sql",
            }
            tab_names = []
            for lang in task["coding_language"]:
                tab_names.append(lang_name_to_tab_name[lang])

            with st.form("Code"):
                st.form_submit_button(
                    "Run Code",
                    on_click=toggle_show_code_output,
                    disabled=st.session_state.is_ai_running,
                )

                tabs = st.tabs(tab_names)
                for index, tab in enumerate(tabs):
                    with tab:
                        tab_name = tab_names[index].lower()
                        language = tab_name_to_language[tab_names[index]]

                        if tab_name == "react":
                            show_react_help_text()
                        elif tab_name == "sql":
                            show_sql_help_text()

                        st_ace(
                            min_lines=15,
                            theme="monokai",
                            language=language,
                            tab_size=2,
                            key=f"{tab_name}_code",
                            auto_update=True,
                            value=st.session_state[f"{tab_name}_code"],
                            placeholder=f"Write your {language} code here...",
                            height=275,
                        )

        else:
            import streamlit.components.v1 as components

            if not task["tests"]:
                output_container = st.container()
            else:
                tab_names = ["Output", f"Tests ({len(task['tests'])})"]
                output_tab, tests_tab = st.tabs(tab_names)
                output_container = output_tab

                with tests_tab:
                    try:
                        test_results = run_tests(
                            st.session_state.python_code, task["tests"]
                        )
                        num_tests = len(task["tests"])
                        num_tests_passed = len(
                            [
                                result
                                for result in test_results
                                if result["status"] == "passed"
                            ]
                        )
                        if num_tests_passed == num_tests:
                            st.success(f"{num_tests_passed}/{num_tests} tests passed")
                        elif num_tests_passed == 0:
                            st.error(f"{num_tests_passed}/{num_tests} tests passed")
                        else:
                            st.warning(f"{num_tests_passed}/{num_tests} tests passed")

                        for i, (test, result) in enumerate(
                            zip(task["tests"], test_results)
                        ):

                            if result["status"] == "passed":
                                expander_icon = f"✅"
                            elif result["status"] == "failed":
                                expander_icon = f"❌"
                            else:  # timeout
                                expander_icon = f"⏳ "

                            expander_label = f"Test Case #{i+1}"

                            if result["status"] == "passed":
                                expander_color = "green"
                            elif result["status"] == "failed":
                                expander_color = "red"
                            else:  # timeout
                                expander_color = "yellow"

                            with st.expander(expander_label, icon=expander_icon):
                                st.markdown("**Inputs**", help=test["description"])
                                for input_text in test["input"]:
                                    st.markdown(input_text)
                                st.write("**Expected Output**")
                                st.write(test["output"])
                                st.write("**Actual Output**")
                                st.write(result["output"])

                    except ValueError as e:
                        st.error(str(e))

            with output_container:
                if any(
                    lang in task["coding_language"]
                    for lang in coding_languages_supported
                ):
                    with st.expander("Configuration"):
                        dim_cols = st.columns(2)
                        height = dim_cols[0].slider(
                            "Preview Height",
                            min_value=100,
                            max_value=1000,
                            value=300,
                            on_change=retain_code,
                        )
                        width = dim_cols[1].slider(
                            "Preview Width",
                            min_value=100,
                            max_value=600,
                            value=600,
                            on_change=retain_code,
                        )

                try:
                    with st.container(border=True):
                        if "HTML" in task["coding_language"]:
                            components.html(
                                get_preview_code(),
                                width=width,
                                height=height,
                                scrolling=True,
                            )
                        elif "Javascript" in task["coding_language"]:
                            execute_code(st.session_state.js_code, "Javascript")
                        elif "NodeJS" in task["coding_language"]:
                            execute_code(st.session_state.nodejs_code, "NodeJS")
                        elif "Python" in task["coding_language"]:
                            execute_code(st.session_state.python_code, "Python")
                        elif "React" in task["coding_language"]:
                            execute_code(
                                st.session_state.react_code,
                                "React",
                                width=width,
                                height=height,
                            )
                        elif "SQL" in task["coding_language"]:
                            execute_code(
                                st.session_state.sql_code,
                                "SQL",
                                width=width,
                                height=height,
                            )
                        else:
                            st.write("**No output to show**")
                        # TODO: support for only JS
                        # TODO: support for other languages
                except Exception as e:
                    st.error(f"Error: {e}")

            close_preview_button_col.button(
                "Back to Editor", on_click=toggle_show_code_output
            )

            if submit_button_col.button(
                "Submit Code",
                type="primary",
                disabled=st.session_state.is_ai_running,
                on_click=set_ai_running,
            ):
                get_ai_feedback_on_code()

user_response_placeholder = "Your response"

if task["type"] == "coding":
    user_response_placeholder = (
        "Use the code editor for submitting code and ask/tell anything else here"
    )
else:
    user_response_placeholder = "Write your response here"

# st.session_state.chat_history
# st.session_state.ai_chat_history.messages


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

    if user_response := st.chat_input(
        user_response_placeholder,
        key="report_input",
        on_submit=set_ai_running,
        disabled=st.session_state.is_ai_running,
    ):
        get_ai_feedback_report(user_response)


if task["response_type"] == "chat":
    if chat_input_container:
        with chat_input_container:
            show_and_handle_chat_input()
    else:
        show_and_handle_chat_input()
else:
    show_and_handle_report_input()
