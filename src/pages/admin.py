from typing import List, Dict, Literal
import itertools
import traceback
import math
from datetime import datetime
import asyncio
from functools import partial
import numpy as np
import streamlit as st
import json
from email_validator import validate_email, EmailNotValidError

st.set_page_config(
    page_title="Admin | SensAI", layout="wide", initial_sidebar_state="collapsed"
)

from copy import deepcopy
import pandas as pd
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from lib.llm import (
    get_llm_input_messages,
    call_llm_and_parse_output,
    COMMON_INSTRUCTIONS,
)
from lib.ui import show_singular_or_plural
from lib.config import (
    group_role_learner,
    group_role_mentor,
    task_ai_response_types,
    allowed_input_types,
)
from lib.init import init_env_vars, init_db
from lib.cache import (
    clear_course_cache_for_cohorts,
    clear_cohort_cache_for_courses,
)
from lib.db import (
    get_all_tasks_for_org_or_course,
    store_task as store_task_to_db,
    delete_tasks as delete_tasks_from_db,
    update_task as update_task_in_db,
    update_column_for_task_ids,
    update_tests_for_task,
    create_cohort,
    get_all_cohorts_for_org,
    get_cohort_by_id,
    get_all_milestones_for_org,
    get_all_tags_for_org,
    create_bulk_tags,
    create_tag as create_tag_in_db,
    delete_tag as delete_tag_from_db,
    insert_milestone as insert_milestone_to_db,
    delete_milestone as delete_milestone_from_db,
    update_milestone_color as update_milestone_color_in_db,
    get_all_cv_review_usage,
    get_org_users,
    add_user_to_org_by_email,
    add_members_to_cohort,
    create_cohort_group,
    delete_cohort_group_from_db,
    delete_cohort,
    remove_members_from_cohort,
    update_cohort_group_name,
    add_members_to_cohort_group,
    remove_members_from_cohort_group,
    get_courses_for_tasks,
    add_tasks_to_courses,
    remove_tasks_from_courses,
    add_scoring_criteria_to_task,
    add_scoring_criteria_to_tasks,
    create_course,
    get_all_courses_for_org,
    add_course_to_cohorts,
    add_courses_to_cohort,
    remove_course_from_cohorts,
    remove_courses_from_cohort,
    delete_course,
    get_courses_for_cohort,
    get_cohorts_for_course,
    get_tasks_for_course,
    update_course_name as update_course_name_in_db,
    update_cohort_name as update_cohort_name_in_db,
    update_task_orders as update_task_orders_in_db,
)
from lib.utils import find_intersection, generate_random_color
from lib.config import coding_languages_supported
from lib.profile import show_placeholder_icon
from lib.toast import set_toast, show_toast
from auth import (
    redirect_if_not_logged_in,
    unauthorized_redirect_to_home,
    get_hva_org_id,
    get_org_details_from_org_id,
)

init_env_vars()
init_db()

redirect_if_not_logged_in("id")

if "org_id" not in st.query_params:
    unauthorized_redirect_to_home("`org_id` not given. Redirecting to home page...")

st.session_state.org_id = int(st.query_params["org_id"])
st.session_state.org = get_org_details_from_org_id(st.session_state.org_id)


def reset_ai_running():
    st.session_state.is_ai_running = False


def set_ai_running():
    st.session_state.is_ai_running = True


if "is_ai_running" not in st.session_state:
    reset_ai_running()


def show_logo():
    show_placeholder_icon(
        st.session_state.org["name"],
        st.session_state.org["logo_color"],
        dim=100,
        font_size=56,
    )
    st.container(height=10, border=False)


def show_profile_header():
    cols = st.columns([1, 7])

    with cols[0]:
        show_logo()

    with cols[1]:
        st.subheader(st.session_state.org["name"])


show_profile_header()


def refresh_cohorts():
    st.session_state.cohorts = get_all_cohorts_for_org(st.session_state.org_id)


def refresh_courses():
    st.session_state.courses = get_all_courses_for_org(st.session_state.org_id)


def refresh_tasks():
    st.session_state.tasks = get_all_tasks_for_org_or_course(st.session_state.org_id)


def refresh_milestones():
    st.session_state.milestones = get_all_milestones_for_org(st.session_state.org_id)


def refresh_tags():
    st.session_state.tags = get_all_tags_for_org(st.session_state.org_id)


if "cohorts" not in st.session_state:
    refresh_cohorts()

if "courses" not in st.session_state:
    refresh_courses()

if "milestones" not in st.session_state:
    refresh_milestones()

if "tags" not in st.session_state:
    refresh_tags()


def reset_tests():
    st.session_state.tests = []


if "tests" not in st.session_state:
    reset_tests()

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = ""

if "final_answer" not in st.session_state:
    st.session_state.final_answer = ""


def refresh_scoring_criteria():
    st.session_state.scoring_criteria = []


if "scoring_criteria" not in st.session_state:
    refresh_scoring_criteria()

if "task_uploader_key" not in st.session_state:
    st.session_state.task_uploader_key = 0


def update_task_uploader_key():
    st.session_state.task_uploader_key += 1


if "cohort_uploader_key" not in st.session_state:
    st.session_state.cohort_uploader_key = 0


def update_cohort_uploader_key():
    st.session_state.cohort_uploader_key += 1


show_toast()

# model = st.sidebar.selectbox(
#     "Model",
#     [
#         {"label": "gpt-4o", "version": "gpt-4o-2024-08-06"},
#         {"label": "gpt-4o-mini", "version": "gpt-4o-mini-2024-07-18"},
#     ],
#     format_func=lambda val: val["label"],
# )

model = {"label": "gpt-4o", "version": "gpt-4o-2024-08-06"}


async def generate_answer_for_task(task_name, task_description, verbose=True):
    system_prompt_template = """You are a helpful and encouraging tutor.\n\nYou will be given a task that has been assigned to a student along with its description.\n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description and completely adhere to the requirements without making up anything on your own that is not already present in the description.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = (
        """Task name: {task_name}\n\nTask description: {task_description}"""
    )

    class Output(BaseModel):
        solution: str = Field(
            title="solution",
            description="The solution to the task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model["version"],
            output_parser=output_parser,
            max_tokens=2048,
            verbose=verbose,
            # labels=["final_answers", "audit rights"],
            # model_type=model_type,
        )
        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()
        raise Exception


@st.spinner("Generating answer...")
def generate_answer_for_form_task(verbose=True):
    st.session_state.ai_answer = asyncio.run(
        generate_answer_for_task(
            st.session_state.task_name, st.session_state.task_description, verbose
        )
    )


def convert_tests_to_prompt(tests: List[Dict]) -> str:
    if not tests:
        return ""

    return "\n-----------------\n".join(
        [f"Input:\n{test['input']}\n\nOutput:\n{test['output']}" for test in tests]
    )


async def generate_tests_for_task_from_llm(
    task_name, task_description, num_test_inputs, tests
):
    system_prompt_template = """You are a test case generator for programming tasks.\n\nYou will be given a task name, its description, the number of inputs expected and, optionally, a list of test cases.\n\nYou need to generate a list of test cases in the form of input/output pairs.\n\n- Give some reasoning before arriving at the answer but keep it concise.\n- Create diverse test cases that cover various scenarios, including edge cases.\n- Ensure the test cases are relevant to the task description.\n- Provide at least 3 test cases, but no more than 5.\n- Ensure that every test case is unique.\n- If you are given a list of test cases, you need to ensure that the new test cases you generate are not duplicates of the ones in the list.\n{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name: {task_name}\n\nTask description: {task_description}\n\nNumber of inputs: {num_test_inputs}\n\nTest cases:\n\n{tests}"""

    class TestCase(BaseModel):
        input: List[str] = Field(
            description="The list of inputs for a single test case. The number of inputs is {num_test_inputs}. Always return a list"
        )
        output: str = Field(description="The expected output for the test case")
        description: str = Field(
            description="A very brief description of the test case", default=""
        )

    class Output(BaseModel):
        test_cases: List[TestCase] = Field(
            description="A list of test cases for the given task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    # import ipdb; ipdb.set_trace()

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
        num_test_inputs=num_test_inputs,
        tests=convert_tests_to_prompt(tests),
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model["version"],
            output_parser=output_parser,
            max_tokens=2048,
            verbose=True,
        )
        return [
            {
                "input": tc["input"],
                "output": tc["output"],
                "description": tc["description"],
            }
            for tc in pred_dict["test_cases"]
        ]
    except Exception as exception:
        traceback.print_exc()
        raise exception


async def generate_tests_for_task(
    task_name: str, task_description: str, num_test_inputs: int, tests: List[Dict]
):
    with st.spinner("Generating tests..."):
        generated_tests = await generate_tests_for_task_from_llm(
            task_name,
            task_description,
            num_test_inputs,
            tests,
        )

    st.session_state.tests.extend(generated_tests)


def delete_test_from_session_state(test_index):
    st.session_state.tests.pop(test_index)


def update_test_in_session_state(test_index):
    st.session_state.tests[test_index] = {
        "input": [
            st.session_state[f"test_input_{test_index}_{i}"]
            for i in range(len(st.session_state.tests[test_index]["input"]))
        ],
        "output": st.session_state[f"test_output_{test_index}"],
        "description": st.session_state[f"test_description_{test_index}"],
    }


def validate_task_metadata_params():
    error_text = ""
    if not st.session_state.ai_response_type:
        error_text = "Please select the AI response type"
    elif not st.session_state.task_type:
        error_text = "Please select a task type"
    elif (
        st.session_state.task_type == "coding" and not st.session_state.coding_languages
    ):
        error_text = "Please select at least one coding language"
    elif (
        st.session_state.ai_response_type == "report"
        and not st.session_state.scoring_criteria
    ):
        error_text = "Please add at least one scoring criterion for the report"

    return error_text


def add_verified_task_to_list(final_answer):
    error_text = ""
    if not st.session_state.task_name:
        error_text = "Please enter a task name"
    elif not st.session_state.task_description:
        error_text = "Please enter a task description"
    elif st.session_state.ai_response_type == "chat" and not final_answer:
        error_text = "Please enter an answer"
    else:
        error_text = validate_task_metadata_params()
    if error_text:
        st.error(error_text)
        return

    task_id = store_task_to_db(
        st.session_state.task_name,
        st.session_state.task_description,
        final_answer,
        st.session_state.task_tags,
        st.session_state.task_type,
        st.session_state.ai_response_type,
        st.session_state.coding_languages,
        model["version"],
        True,
        st.session_state.tests,  # Add this line to include the tests
        st.session_state.milestone["id"] if st.session_state.milestone else None,
        st.session_state.org_id,
    )

    if st.session_state.selected_task_courses:
        add_tasks_to_courses(
            [
                [task_id, course["id"]]
                for course in st.session_state.selected_task_courses
            ]
        )

    if st.session_state.scoring_criteria:
        add_scoring_criteria_to_task(task_id, st.session_state.scoring_criteria)

    refresh_tasks()
    reset_tests()
    st.rerun()


def add_tests_to_task(
    task_name: str, task_description: str, mode: Literal["add", "edit"]
):
    container = st.container()
    cols = st.columns([3.5, 1])

    show_toast()

    if st.session_state.tests:
        num_test_inputs = len(st.session_state.tests[0]["input"])
        header_container = cols[0]
    else:
        header_container = container
        num_test_inputs = cols[0].number_input("Number of inputs", min_value=1, step=1)
        cols[-1].markdown("####")

    header_container.subheader("Add tests")
    if cols[-1].button("Generate", key="generate_tests"):
        asyncio.run(
            generate_tests_for_task(
                task_name, task_description, num_test_inputs, st.session_state.tests
            )
        )

    for test_index, test in enumerate(st.session_state.tests):
        with st.expander(f"Test {test_index + 1}"):
            st.text("Inputs")
            for i, input_value in enumerate(test["input"]):
                st.text_area(
                    label=f"Input {i + 1}",
                    value=input_value,
                    key=f"test_input_{test_index}_{i}",
                    on_change=update_test_in_session_state,
                    args=(test_index,),
                    label_visibility="collapsed",
                )

            st.text("Output")
            st.text_area(
                label="Output",
                value=test["output"],
                key=f"test_output_{test_index}",
                on_change=update_test_in_session_state,
                args=(test_index,),
                label_visibility="collapsed",
            )
            st.text("Description (optional)")
            st.text_area(
                label="Description",
                value=test.get("description", ""),
                key=f"test_description_{test_index}",
                on_change=update_test_in_session_state,
                args=(test_index,),
                label_visibility="collapsed",
            )
            cols = st.columns([3, 1.1, 1])
            is_delete_disabled = mode == "edit" and len(st.session_state.tests) == 1
            cols[-1].button(
                "Delete",
                type="primary",
                on_click=delete_test_from_session_state,
                args=(test_index,),
                key=f"delete_test_{test_index}",
                disabled=is_delete_disabled,
                help=(
                    "To delete all tests, use the `Delete all tests` button below"
                    if is_delete_disabled
                    else ""
                ),
            )

    st.text("Inputs")
    for i in range(num_test_inputs):
        st.text_area(
            f"Input {i + 1}", key=f"new_test_input_{i}", label_visibility="collapsed"
        )

    st.text("Output")
    st.text_area("Output", key="test_output", label_visibility="collapsed")
    st.text("Description (optional)")
    st.text_area("Description", key="test_description", label_visibility="collapsed")

    def add_test():
        st.session_state.tests.append(
            {
                "input": [
                    st.session_state[f"new_test_input_{i}"]
                    for i in range(num_test_inputs)
                ],
                "output": st.session_state.test_output,
                "description": st.session_state.test_description,
            }
        )
        for i in range(num_test_inputs):
            st.session_state[f"new_test_input_{i}"] = ""

        st.session_state.test_output = ""
        st.session_state.test_description = ""
        set_toast("Added test!")

    st.info(
        "Tip: Click outside the boxes above after you are done typing the last input before clicking the button below"
    )
    st.button("Add Test", on_click=add_test)

    # st.session_state.tests


def update_tests_for_task_in_db(task_id: int, tests, toast_message: str = None):
    update_tests_for_task(task_id, tests)
    refresh_tasks()
    reset_tests()
    set_toast(toast_message)


@st.dialog("Edit tests for task")
def edit_tests_for_task(
    df,
    task_id,
):
    task_details = df[df["id"] == task_id].iloc[0]
    if not st.session_state.tests:
        st.session_state.tests = deepcopy(task_details["tests"])

    add_tests_to_task(
        task_details["name"],
        task_details["description"],
        mode="edit",
    )

    cols = st.columns(2) if st.session_state.tests else st.columns(1)

    is_tests_updated = task_details["tests"] != st.session_state.tests
    if cols[0].button(
        "Update tests",
        type="primary",
        use_container_width=True,
        disabled=not is_tests_updated,
        help=(
            "Nothing to update"
            if task_details["tests"] == st.session_state.tests
            else ""
        ),
    ):
        update_tests_for_task_in_db(
            task_id,
            st.session_state.tests,
            toast_message="Tests updated successfully!",
        )
        st.rerun()

    if len(cols) == 2:
        if cols[1].button(
            "Delete all tests",
            type="primary" if not is_tests_updated else "secondary",
            use_container_width=True,
        ):
            update_tests_for_task_in_db(task_id, [], "Tests deleted successfully!")
            st.rerun()


def milestone_selector():
    return st.selectbox(
        "Milestone",
        st.session_state.milestones,
        key="milestone",
        format_func=lambda row: row["name"],
        index=None,
        help="If you don't see the milestone you want, you can create a new one from the `Milestones` tab",
    )


def cohort_selector(default=None):
    return st.multiselect(
        "Cohorts",
        st.session_state.cohorts,
        key="course_cohorts",
        default=default,
        format_func=lambda row: row["name"],
        help="If you don't see the cohort you want, you can create a new one from the `Cohorts` tab",
    )


def course_selector(key_prefix: str, default=None):
    return st.multiselect(
        "Courses",
        st.session_state.courses,
        default=default,
        key=f"selected_{key_prefix}_courses",
        format_func=lambda row: row["name"],
        help="If you don't see the course you want, you can create a new one from the `Courses` tab",
    )


def task_input_type_selector():
    task_input_types = allowed_input_types[st.session_state.ai_response_type]
    default_index = None
    if len(task_input_types) == 1:
        default_index = 0

    return st.selectbox(
        "Select task type", task_input_types, key="task_type", index=default_index
    )


def clear_task_input_type():
    if "task_type" in st.session_state:
        del st.session_state.task_type


def ai_response_type_selector():
    return st.selectbox(
        "Select AI response type",
        task_ai_response_types,
        key="ai_response_type",
        index=task_ai_response_types.index("chat"),
        on_change=clear_task_input_type,
    )


def coding_language_selector():
    if (
        "coding_languages" in st.session_state
        and st.session_state.coding_languages is None
    ):
        st.session_state.coding_languages = []

    return st.multiselect(
        "Code editor language (s)",
        coding_languages_supported,
        help="Choose or more languages to show in the code editor",
        key="coding_languages",
    )


def add_scoring_criterion():
    st.session_state.scoring_criteria.append(
        {
            "category": st.session_state.new_scoring_criterion_category,
            "description": st.session_state.new_scoring_criterion_description,
            "range": [
                st.session_state.new_scoring_criterion_range_start,
                st.session_state.new_scoring_criterion_range_end,
            ],
        }
    )

    st.session_state.new_scoring_criterion_category = ""
    st.session_state.new_scoring_criterion_description = ""
    st.session_state.new_scoring_criterion_range_start = 0
    st.session_state.new_scoring_criterion_range_end = 1


def update_scoring_criterion(index: int):
    st.session_state.scoring_criteria[index] = {
        "category": st.session_state[f"scoring_criterion_category_{index}"],
        "description": st.session_state[f"scoring_criterion_description_{index}"],
        "range": [
            st.session_state[f"scoring_criterion_range_start_{index}"],
            st.session_state[f"scoring_criterion_range_end_{index}"],
        ],
    }


def show_scoring_criteria_addition_form():
    st.subheader("Scoring Criterion")
    for index, scoring_criterion in enumerate(st.session_state.scoring_criteria):
        with st.expander(
            f"{scoring_criterion['category']} ({scoring_criterion['range'][0]} - {scoring_criterion['range'][1]})"
        ):
            updated_category = st.text_input(
                "Category",
                value=scoring_criterion["category"],
                key=f"scoring_criterion_category_{index}",
            )
            updated_description = st.text_input(
                "Description",
                value=scoring_criterion["description"],
                key=f"scoring_criterion_description_{index}",
            )
            cols = st.columns(2)
            updated_range_start = cols[0].number_input(
                "Min Score",
                min_value=0,
                step=1,
                value=scoring_criterion["range"][0],
                key=f"scoring_criterion_range_start_{index}",
            )
            range_end_min_value = updated_range_start + 1
            range_end_default_value = (
                scoring_criterion["range"][1]
                if scoring_criterion["range"][1] >= range_end_min_value
                else range_end_min_value
            )
            updated_range_end = cols[1].number_input(
                "Max Score",
                min_value=range_end_min_value,
                step=1,
                value=range_end_default_value,
                key=f"scoring_criterion_range_end_{index}",
            )

            if (
                updated_category != scoring_criterion["category"]
                or updated_description != scoring_criterion["description"]
                or updated_range_start != scoring_criterion["range"][0]
                or updated_range_end != scoring_criterion["range"][1]
            ):
                st.button(
                    "Update Criterion",
                    type="primary",
                    use_container_width=True,
                    on_click=update_scoring_criterion,
                    args=(index,),
                )

    new_category = st.text_input(
        "Add a new category to the scoring criterion",
        placeholder="e.g. Correctness",
        key="new_scoring_criterion_category",
    )
    new_description = st.text_area(
        "Add a description for the new category",
        placeholder="e.g. The answer provided is correct",
        key="new_scoring_criterion_description",
    )
    cols = st.columns(2)
    range_start = cols[0].number_input(
        "Lowest possible score for this category",
        min_value=0,
        step=1,
        key="new_scoring_criterion_range_start",
    )
    range_end = cols[1].number_input(
        "Highest possible score for this category",
        min_value=range_start + 1,
        step=1,
        key="new_scoring_criterion_range_end",
    )
    st.button("Add category", use_container_width=True, on_click=add_scoring_criterion)
    st.divider()


@st.dialog("Add a new task")
def show_task_form():
    st.text_input("Name", key="task_name")
    st.text_area(
        "Description",
        key="task_description",
    )

    cols = st.columns(2)

    with cols[0]:
        ai_response_type = ai_response_type_selector()

    if not ai_response_type:
        return

    with cols[1]:
        task_type = task_input_type_selector()

    if task_type == "coding":
        coding_language_selector()

        # test cases
        if st.checkbox("I want to add tests", False):
            add_tests_to_task(
                st.session_state.task_name,
                st.session_state.task_description,
                mode="add",
            )
    else:
        st.session_state.coding_languages = None

    final_answer = None
    if ai_response_type == "chat":
        cols = st.columns([3.5, 1])

        cols[-1].container(height=10, border=False)
        if cols[-1].button(
            "Generate",
            disabled=(
                not st.session_state.task_description
                or not st.session_state.task_name
                or st.session_state.final_answer != ""
                or st.session_state.ai_answer != ""
            ),
            key="generate_answer",
        ):
            with cols[0]:
                generate_answer_for_form_task()

        final_answer = cols[0].text_area(
            "Answer",
            key="final_answer",
            value=st.session_state.ai_answer,
        )
        if not final_answer and st.session_state.ai_answer:
            final_answer = st.session_state.ai_answer

    elif ai_response_type == "report":
        show_scoring_criteria_addition_form()

    st.multiselect(
        "Tags",
        st.session_state.tags,
        key="task_tags",
        default=None,
        format_func=lambda tag: tag["name"],
        help="If you don't see the tag you want, you can create a new one from the `Tags` tab",
    )

    cols = st.columns(2)
    with cols[0]:
        milestone_selector()

    with cols[1]:
        course_selector("task", default=None)

    if st.button(
        "Add task",
        use_container_width=True,
        type="primary",
    ):
        # st.session_state.vote = {"item": item, "reason": reason}
        add_verified_task_to_list(final_answer)


async def generate_answer_for_bulk_task(
    task_row_index, task_name, task_description, verbose=True
):
    answer = await generate_answer_for_task(task_name, task_description, verbose)
    return task_row_index, answer


def update_progress_bar(progress_bar, count, num_tasks, message):
    progress_bar.progress(count / num_tasks, text=f"{message} ({count}/{num_tasks})")


async def generate_answers_for_tasks(tasks_df):
    set_ai_running()
    coroutines = []

    for index, row in tasks_df.iterrows():
        coroutines.append(
            generate_answer_for_bulk_task(
                index, row["Name"], row["Description"], verbose=False
            )
        )

    num_tasks = len(tasks_df)
    progress_bar = st.progress(
        0, text=f"Generating answers for tasks... (0/{num_tasks})"
    )

    count = 0

    tasks_df["Answer"] = [None] * num_tasks

    for completed_task in asyncio.as_completed(coroutines):
        task_row_index, answer = await completed_task

        tasks_df.at[task_row_index, "Answer"] = answer
        count += 1

        update_progress_bar(
            progress_bar, count, num_tasks, "Generating answers for tasks..."
        )

    progress_bar.empty()
    reset_ai_running()
    return tasks_df


def bulk_upload_tasks_to_db(
    tasks_df: pd.DataFrame,
):
    error_text = validate_task_metadata_params()
    if error_text:
        st.error(error_text)
        return

    verified = True
    if st.session_state.ai_response_type == "chat" and "Answer" not in tasks_df.columns:
        tasks_df = asyncio.run(generate_answers_for_tasks(tasks_df))
        verified = False

    has_tags = "Tags" in tasks_df.columns

    if has_tags:
        unique_tags = list(
            set(
                list(
                    itertools.chain(
                        *tasks_df["Tags"]
                        .apply(lambda val: [tag.strip() for tag in val.split(",")])
                        .tolist()
                    )
                )
            )
        )
        has_new_tags = create_bulk_tags(unique_tags, st.session_state.org_id)
        if has_new_tags:
            refresh_tags()

    new_task_ids = []
    for _, row in tasks_df.iterrows():
        task_tags = []
        if has_tags:
            task_tag_names = [tag.strip() for tag in row["Tags"].split(",")]
            task_tags = [
                tag for tag in st.session_state.tags if tag["name"] in task_tag_names
            ]

        if st.session_state.ai_response_type == "chat":
            answer = row["Answer"]
        else:
            answer = None

        task_id = store_task_to_db(
            row["Name"],
            row["Description"],
            answer,
            task_tags,
            st.session_state.task_type,
            st.session_state.ai_response_type,
            st.session_state.coding_languages,
            model["version"],
            verified,
            [],
            (
                st.session_state.milestone["id"]
                if st.session_state.milestone is not None
                else None
            ),
            st.session_state.org_id,
        )
        new_task_ids.append(task_id)

    if st.session_state.selected_task_courses:
        course_tasks_to_add = list(
            itertools.chain(
                *[
                    [(task_id, course["id"]) for task_id in new_task_ids]
                    for course in st.session_state.selected_task_courses
                ]
            )
        )
        add_tasks_to_courses(course_tasks_to_add)

    if st.session_state.scoring_criteria:
        add_scoring_criteria_to_tasks(new_task_ids, st.session_state.scoring_criteria)

    refresh_tasks()
    st.rerun()


@st.dialog("Bulk upload tasks")
def show_bulk_upload_tasks_form():
    cols = st.columns(2)

    with cols[0]:
        ai_response_type = ai_response_type_selector()

    if not ai_response_type:
        return

    with cols[1]:
        task_type = task_input_type_selector()

    if task_type == "coding":
        coding_language_selector()
    else:
        st.session_state.coding_languages = None

    if ai_response_type == "report":
        show_scoring_criteria_addition_form()

    cols = st.columns(2)
    with cols[0]:
        milestone_selector()

    with cols[1]:
        course_selector("task", default=None)

    file_uploader_label = "Choose a CSV file with the columns:\n\n`Name`, `Description`, `Tags` (Optional)"
    if ai_response_type == "chat":
        file_uploader_label += ", `Answer` (optional)"

    uploaded_file = st.file_uploader(
        file_uploader_label,
        type="csv",
        key=f"bulk_upload_tasks_{st.session_state.task_uploader_key}",
    )

    if uploaded_file:
        tasks_df = pd.read_csv(uploaded_file)

        st.dataframe(tasks_df, hide_index=True)

        error_message = None
        for index, row in tasks_df.iterrows():
            if not row["Name"] or (
                isinstance(row["Name"], float) and math.isnan(row["Name"])
            ):
                error_message = f"Task name missing for row {index + 1}"
                break
            if not row["Description"] or (
                isinstance(row["Description"], float) and math.isnan(row["Description"])
            ):
                error_message = f"Task description missing for row {index + 1}"
                break

        if error_message:
            st.error(error_message)
            return

        if st.button(
            "Add tasks",
            use_container_width=True,
            type="primary",
            disabled=st.session_state.is_ai_running,
        ):
            bulk_upload_tasks_to_db(tasks_df)


def delete_tasks_from_list(task_ids):
    delete_tasks_from_db(task_ids)
    refresh_tasks()
    st.rerun()


@st.dialog("Delete tasks")
def show_tasks_delete_confirmation(
    task_ids,
):
    st.write("Are you sure you want to delete the selected tasks?")

    confirm_col, cancel_col, _, _ = st.columns([1, 1, 2, 2])
    if confirm_col.button("Yes", use_container_width=True):
        delete_tasks_from_list(
            task_ids,
        )
        st.rerun()

    if cancel_col.button("No", use_container_width=True, type="primary"):
        st.rerun()


def update_tasks_with_new_value(
    task_ids: List[int],
    column_to_update: str,
    new_value: str,
):
    update_column_for_task_ids(task_ids, column_to_update, new_value)
    refresh_tasks()
    st.rerun()


@st.dialog("Edit tasks")
def show_task_edit_dialog(task_ids):
    column_to_update = st.selectbox(
        "Select a column to update", ["type", "coding_language", "milestone"]
    )
    kwargs = {}
    db_column = None
    if column_to_update == "type":
        option_component = st.selectbox
        options = ["text", "coding"]
    elif column_to_update == "milestone":
        option_component = st.selectbox
        options = st.session_state.milestones
        kwargs["format_func"] = lambda row: row["name"]
        value_key = "id"
        db_column = "milestone_id"
    else:
        option_component = st.multiselect
        options = coding_languages_supported

    new_value = option_component("Select the new value", options, **kwargs)

    st.write("Are you sure you want to update the selected tasks?")

    confirm_col, cancel_col, _, _ = st.columns([1, 1, 2, 2])
    if confirm_col.button("Yes", use_container_width=True):
        if option_component == st.selectbox and isinstance(new_value, dict):
            new_value = new_value[value_key]

        if db_column is None:
            db_column = column_to_update

        update_tasks_with_new_value(task_ids, db_column, new_value)
        st.rerun()

    if cancel_col.button("No", use_container_width=True, type="primary"):
        st.rerun()


@st.dialog("Update courses for tasks")
def show_update_task_courses(task_ids, existing_task_course_pairs):
    # Find courses that all selected tasks belong to
    task_course_dict = {}
    for task_id, course_id in existing_task_course_pairs:
        if task_id not in task_course_dict:
            task_course_dict[task_id] = set()

        task_course_dict[task_id].add(course_id)

    # Get intersection of course IDs across all tasks
    common_course_ids = None
    for task_id in task_ids:
        task_courses = task_course_dict.get(task_id, set())

        if common_course_ids is None:
            common_course_ids = task_courses
            continue

        common_course_ids = common_course_ids.intersection(task_courses)

    # Convert course IDs to course objects for default selection
    default_courses = [
        course
        for course in st.session_state.courses
        if course["id"] in (common_course_ids or set())
    ]

    with st.form("update_task_courses_form", border=False):
        selected_courses = st.multiselect(
            "Select courses to assign tasks to",
            st.session_state.courses,
            format_func=lambda x: x["name"],
            default=default_courses,
        )

        st.container(height=30, border=False)

        if st.form_submit_button("Update", use_container_width=True, type="primary"):
            # our SQL query takes care of existing pairs, so we don't need to filter them here
            course_tasks_to_keep = list(
                itertools.chain(
                    *[
                        [(task_id, course["id"]) for course in selected_courses]
                        for task_id in task_ids
                    ]
                )
            )

            if sorted(course_tasks_to_keep, key=lambda x: x[0]) == sorted(
                existing_task_course_pairs, key=lambda x: x[0]
            ):
                st.error("No changes made")
                return

            course_tasks_to_remove = [
                pair
                for pair in existing_task_course_pairs
                if pair not in course_tasks_to_keep
            ]

            if course_tasks_to_keep:
                add_tasks_to_courses(course_tasks_to_keep)

            if course_tasks_to_remove:
                remove_tasks_from_courses(course_tasks_to_remove)

            st.rerun()


tab_names = ["Cohorts", "Courses", "Tasks", "Milestones", "Tags"]

is_hva_org = get_hva_org_id() == st.session_state.org_id
if is_hva_org:
    tab_names.append("Analytics")

tab_names.append("Settings")

tabs = st.tabs(tab_names)


def show_tasks_tab():
    cols = st.columns([1, 8])

    add_task = cols[0].button("Add a new task", type="primary")

    bulk_upload_tasks = cols[1].button("Bulk upload tasks")

    if add_task:
        reset_tests()
        st.session_state.ai_answer = ""
        st.session_state.final_answer = ""
        refresh_scoring_criteria()
        show_task_form()

    if bulk_upload_tasks:
        refresh_scoring_criteria()
        update_task_uploader_key()
        show_bulk_upload_tasks_form()

    tasks_description = f"You can select multiple tasks by clicking beside the `id` column of each task and do any of the following:\n\n- Update the cohort for the selected tasks\n\n- Edit task attributes in bulk (e.g. task type, coding language in the code editor (for coding tasks only), milestone)\n\n- You can also go through the unverified answers and verify them for learners to access them by selecting `Edit Mode`.\n\n- Add/Modify tests for one task at a time (for coding tasks only)\n\n- Delete tasks"

    with st.expander("User Guide"):
        st.write(tasks_description)

    refresh_tasks()

    if not st.session_state.tasks:
        st.error("No tasks added yet")
        return

    df = pd.DataFrame(st.session_state.tasks)
    df["coding_language"] = df["coding_language"].apply(
        lambda x: x.split(",") if isinstance(x, str) else x
    )
    df["num_tests"] = df["tests"].apply(lambda x: len(x) if isinstance(x, list) else 0)

    cols = st.columns(4)
    tasks_with_tags_df = df[df["tags"].notna()]
    all_tags = np.unique(
        list(itertools.chain(*[tags for tags in tasks_with_tags_df["tags"].tolist()]))
    ).tolist()
    filter_tags = cols[0].multiselect("Filter by tags", all_tags)

    if filter_tags:
        df = df[df["tags"].apply(lambda x: any(tag in x for tag in filter_tags))]

    verified_filter = cols[1].radio(
        "Filter by verification status",
        ["All", "Verified", "Unverified"],
        horizontal=True,
    )

    if verified_filter != "All":
        df = df[df["verified"] == (verified_filter == "Verified")]

    # milestones = [milestone["id"] for milestone in st.session_state.milestones]
    filtered_milestones = cols[2].multiselect(
        "Filter by milestone",
        st.session_state.milestones,
        format_func=lambda x: x["name"],
    )

    if filtered_milestones:
        filtered_milestone_ids = [milestone["id"] for milestone in filtered_milestones]
        df = df[df["milestone_id"].apply(lambda x: x in filtered_milestone_ids)]

    (
        edit_mode_col,
        _,
        save_col,
    ) = st.columns([1.25, 7.5, 1])

    is_edit_mode = edit_mode_col.checkbox(
        "Edit Mode",
        value=False,
        help="Select this to go through the unverified answers and verify them for learners to access them or make any other changes to the tasks.",
    )

    column_config = {
        # 'id': None
        "description": st.column_config.TextColumn(width="medium"),
        "answer": st.column_config.TextColumn(width="medium"),
        "milestone_name": st.column_config.TextColumn(label="milestone"),
    }

    task_id_to_courses = get_courses_for_tasks(df["id"].tolist())
    df["courses"] = df["id"].apply(lambda x: task_id_to_courses[x])

    df["course_names"] = df["courses"].apply(lambda x: [course["name"] for course in x])

    column_order = [
        "id",
        "verified",
        "num_tests",
        "name",
        "description",
        "answer",
        "tags",
        "milestone_name",
        "course_names",
        "type",
        "response_type",
        "coding_language",
        "generation_model",
        "timestamp",
    ]

    def save_changes_in_edit_mode(edited_df):
        # identify the rows that have been changed
        # and update the db with the new values
        # import ipdb; ipdb.set_trace()
        changed_rows = edited_df[(df != edited_df).any(axis=1)]

        print(f"Changed rows: {len(changed_rows)}", flush=True)

        for _, row in changed_rows.iterrows():
            task_id = row["id"]
            # print(task_id)
            update_task_in_db(
                task_id,
                row["name"],
                row["description"],
                row["answer"],
                row["type"],
                row["response_type"],
                row["coding_language"],
                row["generation_model"],
                row["verified"],
            )

        # Refresh the tasks in the session state
        refresh_tasks()
        st.toast("Changes saved successfully!")
        # st.rerun()

    if not is_edit_mode:
        delete_col, update_course_col, edit_col, add_tests_col = st.columns(
            [0.4, 1, 1.2, 6]
        )

        event = st.dataframe(
            df,
            on_select="rerun",
            selection_mode="multi-row",
            hide_index=True,
            use_container_width=True,
            column_config=column_config,
            column_order=column_order,
        )

        if len(event.selection["rows"]):
            task_ids = df.iloc[event.selection["rows"]]["id"].tolist()

            if delete_col.button("🗑️", help="Delete selected tasks"):
                # import ipdb; ipdb.set_trace()
                show_tasks_delete_confirmation(
                    task_ids,
                )

            if update_course_col.button("Update courses"):
                # import ipdb; ipdb.set_trace()
                existing_task_course_pairs = []

                for task_id in task_ids:
                    for course in task_id_to_courses[task_id]:
                        existing_task_course_pairs.append((task_id, course["id"]))

                show_update_task_courses(task_ids, existing_task_course_pairs)

            if edit_col.button("Edit task attributes"):
                # import ipdb; ipdb.set_trace()
                show_task_edit_dialog(
                    task_ids,
                )

            if (
                len(task_ids) == 1
                and df.iloc[event.selection["rows"]]["type"].tolist()[0] == "coding"
            ):
                if add_tests_col.button("Add/Edit tests"):
                    reset_tests()
                    edit_tests_for_task(
                        df,
                        task_ids[0],
                    )

    else:
        edited_df = st.data_editor(
            df,
            hide_index=True,
            column_config=column_config,
            column_order=column_order,
            use_container_width=True,
            disabled=[
                "id",
                "num_tests",
                "type",
                "generation_model",
                "timestamp",
                "milestone_name",
            ],
        )

        if not df.equals(edited_df):
            save_col.button(
                "Save changes",
                type="primary",
                on_click=partial(save_changes_in_edit_mode, edited_df),
            )


with tabs[2]:
    show_tasks_tab()


@st.dialog("Create Cohort")
def show_create_cohort_dialog():
    with st.form("create_cohort_form", border=False):
        cohort_name = st.text_input("Enter cohort name")

        if st.form_submit_button(
            "Create",
            type="primary",
            use_container_width=True,
        ):
            if not cohort_name:
                st.error("Enter a cohort name")
                return

            create_cohort(cohort_name, st.session_state.org_id)
            refresh_cohorts()
            if "tasks" in st.session_state and st.session_state.tasks:
                refresh_tasks()

            set_toast(f"Cohort `{cohort_name}` created successfully!")
            st.rerun()


@st.dialog("Add Members to Cohort")
def show_add_members_to_cohort_dialog(cohort_id: int, cohort_info: dict):
    existing_members = set([member["email"] for member in cohort_info["members"]])

    tabs = st.tabs(["Add Members", "Bulk Upload Members"])

    with tabs[0]:
        with st.form("add_cohort_member_form", border=False):
            member_email = st.text_input("Enter email", key="cohort_member_email")
            role = st.selectbox("Select role", [group_role_learner, group_role_mentor])

            submit_button = st.form_submit_button(
                "Add Member",
                use_container_width=True,
                type="primary",
            )
            if submit_button:
                try:
                    # Check that the email address is valid
                    member_email = validate_email(member_email)

                    if member_email.normalized in existing_members:
                        st.error(
                            f"Member {member_email.normalized} already exists in cohort"
                        )
                        return

                    add_members_to_cohort(cohort_id, [member_email.normalized], [role])
                    refresh_cohorts()
                    set_toast("Member added successfully")
                    st.rerun()
                except EmailNotValidError as e:
                    # The exception message is human-readable explanation of why it's
                    # not a valid (or deliverable) email address.
                    st.error("Invalid email")

    with tabs[1]:
        columns = [
            "Email",
            "Role",
        ]
        uploaded_file = st.file_uploader(
            f"Choose a CSV file with the following columns:\n\n{','.join([f'`{column}`' for column in columns])} (can be either `{group_role_learner}` or `{group_role_mentor}`)",
            type="csv",
            key=f"cohort_uploader_{st.session_state.cohort_uploader_key}",
        )

        if not uploaded_file:
            return

        cohort_df = pd.read_csv(uploaded_file)
        if cohort_df.columns.tolist() != columns:
            st.error("The uploaded file does not have the correct columns.")
            return

        if not cohort_df["Role"].isin([group_role_learner, group_role_mentor]).all():
            st.error(
                f"The uploaded file contains invalid roles. Please ensure that the `Role` column only contains `{group_role_learner}` or `{group_role_mentor}`."
            )
            return

        for email in cohort_df["Email"].tolist():
            try:
                validate_email(email)
            except EmailNotValidError as e:
                st.error(f"Invalid email: {email}")
                return

            if email in existing_members:
                st.error(f"Member {email} already exists in cohort")
                return

        st.dataframe(cohort_df, hide_index=True, use_container_width=True)

        if st.button(
            "Add Members",
            use_container_width=True,
            key="bulk_upload_cohort_members",
            type="primary",
        ):
            add_members_to_cohort(
                cohort_id,
                cohort_df["Email"].tolist(),
                cohort_df["Role"].tolist(),
            )
            refresh_cohorts()
            set_toast(f"Members added to cohort successfully!")
            update_cohort_uploader_key()
            st.rerun()


def group_create_edit_form(
    key: str,
    cohort_id: int,
    cohort_info: dict,
    mode: Literal["create", "edit"] = "create",
    group_id: int = None,
    group_name: str = "",
    learners: List[Dict] = [],
    mentors: List[Dict] = [],
):
    with st.form(key, border=False):
        new_group_name = st.text_input(
            "Enter group name", key="cohort_group_name", value=group_name
        )

        learner_options = [
            member
            for member in cohort_info["members"]
            if member["role"] == group_role_learner
        ]
        default_learners = [learner["id"] for learner in learners]
        default_learners_selected = [
            learner for learner in learner_options if learner["id"] in default_learners
        ]

        selected_learners = st.multiselect(
            "Select learners",
            learner_options,
            key="cohort_group_learners",
            format_func=lambda x: x["email"],
            default=default_learners_selected,
        )

        mentor_options = [
            member
            for member in cohort_info["members"]
            if member["role"] == group_role_mentor
        ]
        default_mentors = [mentor["id"] for mentor in mentors]
        default_mentors_selected = [
            mentor for mentor in mentor_options if mentor["id"] in default_mentors
        ]

        selected_mentors = st.multiselect(
            "Select mentors",
            mentor_options,
            key="cohort_group_mentors",
            format_func=lambda x: x["email"],
            default=default_mentors_selected,
        )

        form_submit_button_text = "Create Group" if mode == "create" else "Save Changes"

        if st.form_submit_button(
            form_submit_button_text,
            use_container_width=True,
            type="primary",
        ):
            if not new_group_name:
                st.error("Enter a group name")
                return

            if not selected_learners:
                st.error("Select at least one learner")
                return

            if not selected_mentors:
                st.error("Select at least one mentor")
                return

            if mode == "create":
                create_cohort_group(
                    new_group_name,
                    cohort_id,
                    [member["id"] for member in selected_learners + selected_mentors],
                )
                set_toast(f"Cohort group created successfully!")
            else:
                if new_group_name != group_name:
                    update_cohort_group_name(group_id, new_group_name)

                if selected_learners != learners or selected_mentors != mentors:
                    existing_member_ids = [learner["id"] for learner in learners] + [
                        mentor["id"] for mentor in mentors
                    ]
                    new_member_ids = [
                        learner["id"] for learner in selected_learners
                    ] + [mentor["id"] for mentor in selected_mentors]

                    member_ids_to_add = [
                        member_id
                        for member_id in new_member_ids
                        if member_id not in existing_member_ids
                    ]
                    add_members_to_cohort_group(group_id, member_ids_to_add)

                    member_ids_to_remove = [
                        member_id
                        for member_id in existing_member_ids
                        if member_id not in new_member_ids
                    ]
                    remove_members_from_cohort_group(group_id, member_ids_to_remove)

                set_toast(f"Cohort group updated successfully!")

            refresh_cohorts()
            st.rerun()


@st.dialog("Create Cohort Groups")
def show_create_groups_dialog(cohort_id: int, cohort_info: dict):
    group_create_edit_form(
        "create_groups_form",
        cohort_id,
        cohort_info,
    )


@st.dialog("Edit Cohort Group")
def show_edit_cohort_group_dialog(
    cohort_id: int,
    cohort_info: dict,
    group: Dict,
    learners: List[Dict],
    mentors: List[Dict],
):
    group_create_edit_form(
        "edit_groups_form",
        cohort_id,
        cohort_info,
        mode="edit",
        group_id=group["id"],
        group_name=group["name"],
        learners=learners,
        mentors=mentors,
    )


@st.dialog("Delete Cohort Group Confirmation")
def show_delete_cohort_group_confirmation_dialog(group):
    st.markdown(f"Are you sure you want to delete the group: `{group['name']}`?")
    (
        confirm_col,
        cancel_col,
    ) = st.columns([1.5, 6])

    if confirm_col.button("Confirm", type="primary"):
        delete_cohort_group_from_db(group["id"])
        refresh_cohorts()
        set_toast("Cohort group deleted successfully!")
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


@st.dialog("Remove Members from Cohort Confirmation")
def show_cohort_members_delete_confirmation_dialog(cohort_id: int, members: List[Dict]):
    st.markdown(
        f"Are you sure you want to delete the following members from cohort: {', '.join([member['email'] for member in members])}?"
    )
    (
        confirm_col,
        cancel_col,
    ) = st.columns([1.5, 6])

    if confirm_col.button("Confirm", type="primary"):
        remove_members_from_cohort(cohort_id, [member["id"] for member in members])
        refresh_cohorts()
        set_toast("Members removed from cohort successfully!")
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


@st.dialog("Delete Cohort Confirmation")
def show_delete_cohort_confirmation_dialog(cohort_id: int, cohort_info: Dict):
    st.markdown(f"Are you sure you want to delete the cohort: `{cohort_info['name']}`?")
    (
        confirm_col,
        cancel_col,
    ) = st.columns([1.5, 6])

    if confirm_col.button("Confirm", type="primary"):
        delete_cohort(cohort_id)
        refresh_cohorts()

        # invalidate cache
        clear_cohort_cache_for_courses(cohort_info["courses"])

        set_toast("Cohort deleted successfully!")
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


@st.dialog("Update Cohort Courses")
def show_update_cohort_courses_dialog(cohort_id: int, cohort_courses: List[Dict]):
    with st.form("update_cohort_courses_form", border=False):
        selected_courses = course_selector("cohort", default=cohort_courses)

        st.container(height=10, border=False)

        has_changes = selected_courses != cohort_courses

        if st.form_submit_button(
            "Update",
            type="primary",
            use_container_width=True,
        ):
            if not has_changes:
                st.error("No changes made")
                return

            courses_to_delete = [
                course for course in cohort_courses if course not in selected_courses
            ]
            courses_to_add = [
                course for course in selected_courses if course not in cohort_courses
            ]
            if courses_to_add:
                add_courses_to_cohort(
                    cohort_id, [course["id"] for course in courses_to_add]
                )
            if courses_to_delete:
                remove_courses_from_cohort(
                    cohort_id, [course["id"] for course in courses_to_delete]
                )

            refresh_cohorts()

            # invalidate cache
            clear_course_cache_for_cohorts([cohort_id])
            clear_cohort_cache_for_courses(courses_to_add + courses_to_delete)

            set_toast("Cohort updated successfully!")
            st.rerun()


def show_cohort_courses(selected_cohort: Dict):
    cols = st.columns([1, 0.4])
    with cols[0]:
        if not selected_cohort["courses"]:
            st.markdown("#### Courses")
            st.info("No courses in this cohort")
            cols[1].container(height=40, border=False)
        else:
            st.pills(
                "Courses",
                selected_cohort["courses"],
                format_func=lambda x: x["name"],
                disabled=True,
            )
            cols[1].container(height=5, border=False)

    if cols[1].button("Update", key="update_cohort_courses"):
        show_update_cohort_courses_dialog(
            selected_cohort["id"], selected_cohort["courses"]
        )


def show_cohort_overview(selected_cohort: Dict):
    st.subheader("Overview")
    cohort_info = get_cohort_by_id(selected_cohort["id"])
    cols = st.columns([1, 2, 3.5])
    if cols[0].button("Add Members"):
        show_add_members_to_cohort_dialog(selected_cohort["id"], cohort_info)
    if cols[1].button("Create Groups"):
        show_create_groups_dialog(selected_cohort["id"], cohort_info)

    learners = []
    mentors = []

    # Iterate through all groups in the cohort
    for member in cohort_info["members"]:
        if member["role"] == group_role_learner:
            learners.append(member)
        elif member["role"] == group_role_mentor:
            mentors.append(member)

    tab_names = ["Learners", "Mentors", "Groups"]

    tabs = st.tabs(tab_names)

    def _show_users_tab(users: List[Dict], key: str):
        selection_action_container = st.container(
            key=f"selected_cohort_members_actions_{key}"
        )

        event = st.dataframe(
            pd.DataFrame(users, columns=["email"]),
            on_select="rerun",
            selection_mode="multi-row",
            hide_index=True,
            use_container_width=True,
        )

        if len(event.selection["rows"]):
            if selection_action_container.button(
                "Remove members", key=f"remove_cohort_members_{key}"
            ):
                show_cohort_members_delete_confirmation_dialog(
                    selected_cohort["id"],
                    [users[i] for i in event.selection["rows"]],
                )

    def show_learners_tab():
        if not learners:
            st.info("No learners in this cohort")
            return

        _show_users_tab(learners, "learners")

    def show_mentors_tab():
        if not mentors:
            st.info("No mentors in this cohort")
            return

        _show_users_tab(mentors, "mentors")

    def show_groups_tab(cohort_info):
        if not cohort_info["groups"]:
            st.info("No groups in this cohort")
            return

        cols = st.columns([1, 0.4, 1.8])

        # NOTE: DO NOT REMOVE THIS FORMATTING FOR THE DROPDOWN
        # OTHERWISE CHANGES IN THE COHORT LIKE ADDING/REMOVING MEMBERS
        # FROM THE WHOLE COHORT OR FROM A GROUP WILL NOT REFLECT IN THE DROPDOWN
        # WITHOUT AN EXPLICIT RERUN
        # FOR SOME REASON, ALTHOUGH cohort_info['groups'] IS UPDATED,
        # THE GROUP VIEW DOES NOT UPDATE UNLESS THE MEMBER INFO OF THE GROUP IS
        # USED IN THE FORMATTING OF THE DROPDOWN OPTIONS
        def format_group(group):
            group_mentors = [
                member
                for member in group["members"]
                if member["role"] == group_role_mentor
            ]
            group_learners = [
                member
                for member in group["members"]
                if member["role"] == group_role_learner
            ]
            return f'{group["name"]} ({show_singular_or_plural(len(group_learners), "learner")}, {show_singular_or_plural(len(group_mentors), "mentor")})'

        selected_group = cols[0].selectbox(
            "Select a group",
            cohort_info["groups"],
            format_func=format_group,
        )

        learners = [
            member
            for member in selected_group["members"]
            if member["role"] == group_role_learner
        ]

        mentors = [
            member
            for member in selected_group["members"]
            if member["role"] == group_role_mentor
        ]

        cols[1].container(height=10, border=False)
        cols[1].button(
            "Edit Group",
            on_click=show_edit_cohort_group_dialog,
            args=(
                selected_cohort["id"],
                cohort_info,
                selected_group,
                learners,
                mentors,
            ),
        )
        cols[2].container(height=10, border=False)
        cols[2].button(
            "Delete Group",
            type="primary",
            on_click=show_delete_cohort_group_confirmation_dialog,
            args=(selected_group,),
        )

        cols = st.columns([2, 0.2, 1])

        with cols[0]:
            learners_df = pd.DataFrame(learners)

            st.subheader("Learners")
            st.dataframe(
                learners_df,
                hide_index=True,
                use_container_width=True,
                column_order=["email"],
            )

        with cols[-1]:
            st.subheader("Mentors")
            mentors_df = pd.DataFrame(mentors)
            st.dataframe(
                mentors_df,
                hide_index=True,
                use_container_width=True,
                column_order=["email"],
            )

    with tabs[0]:
        show_learners_tab()

    with tabs[1]:
        show_mentors_tab()

    with tabs[2]:
        show_groups_tab(cohort_info)


def update_cohort_name(cohort, new_name):
    if new_name == cohort["name"]:
        st.toast("No changes made")
        return

    update_cohort_name_in_db(cohort["id"], new_name)
    refresh_cohorts()

    # invalidate cache
    clear_cohort_cache_for_courses(cohort["courses"])

    set_toast("Cohort name updated successfully!")
    st.rerun()


def show_cohort_name_update_form(selected_cohort):
    with st.form("update_cohort_name_form", border=False):
        cols = st.columns([1, 0.4])
        updated_cohort_name = cols[0].text_input(
            "Cohort Name", value=selected_cohort["name"]
        )
        cols[1].container(height=10, border=False)
        if cols[1].form_submit_button("Update"):
            update_cohort_name(selected_cohort, updated_cohort_name)


def show_cohorts_tab():
    cols = st.columns([1.2, 0.5, 3])
    selected_cohort = cols[0].selectbox(
        "Select a cohort", st.session_state.cohorts, format_func=lambda row: row["name"]
    )

    cols[1].container(height=10, border=False)
    if cols[1].button("Create Cohort", type="primary"):
        show_create_cohort_dialog()

    if not len(st.session_state.cohorts):
        st.error("No cohorts added yet")
        return

    if not selected_cohort:
        return

    selected_cohort["courses"] = get_courses_for_cohort(selected_cohort["id"])

    st.divider()

    main_tab_cols = st.columns([0.4, 0.05, 1])

    with main_tab_cols[0]:
        show_cohort_name_update_form(selected_cohort)
        show_cohort_courses(selected_cohort)
        st.container(height=10, border=False)
        if st.button("Delete Cohort", icon="🗑️"):
            show_delete_cohort_confirmation_dialog(
                selected_cohort["id"], selected_cohort
            )

    with main_tab_cols[-1]:
        show_cohort_overview(selected_cohort)


with tabs[0]:
    show_cohorts_tab()


@st.dialog("Create Course")
def show_create_course_dialog():
    with st.form("create_course_form", border=False):
        course_name = st.text_input("Enter course name")

        cohort_selector()

        if st.form_submit_button(
            "Create",
            type="primary",
            use_container_width=True,
        ):
            if not course_name:
                st.error("Enter a course name")
                return

            new_course_id = create_course(course_name, st.session_state.org_id)

            if st.session_state.course_cohorts:
                add_course_to_cohorts(
                    new_course_id,
                    [cohort["id"] for cohort in st.session_state.course_cohorts],
                )
                # invalidate cache
                clear_course_cache_for_cohorts(st.session_state.course_cohorts)

            refresh_courses()
            set_toast(f"Course `{course_name}` created successfully!")
            st.rerun()


@st.dialog("Update Course Cohorts")
def show_update_course_cohorts_dialog(course_id: int, course_cohorts: List[Dict]):
    with st.form("update_course_cohorts_form", border=False):
        selected_cohorts = cohort_selector(default=course_cohorts)

        st.container(height=10, border=False)

        has_changes = selected_cohorts != course_cohorts

        if st.form_submit_button(
            "Update",
            type="primary",
            use_container_width=True,
        ):
            if not has_changes:
                st.error("No changes made")
                return

            cohorts_to_delete_from = [
                cohort for cohort in course_cohorts if cohort not in selected_cohorts
            ]
            cohorts_to_add_to = [
                cohort for cohort in selected_cohorts if cohort not in course_cohorts
            ]
            if cohorts_to_add_to:
                add_course_to_cohorts(
                    course_id, [cohort["id"] for cohort in cohorts_to_add_to]
                )
            if cohorts_to_delete_from:
                remove_course_from_cohorts(
                    course_id, [cohort["id"] for cohort in cohorts_to_delete_from]
                )

            refresh_courses()

            # invalidate cache
            clear_cohort_cache_for_courses([course_id])
            clear_course_cache_for_cohorts(cohorts_to_add_to + cohorts_to_delete_from)

            set_toast("Cohorts updated successfully!")
            st.rerun()


@st.dialog("Delete Course Confirmation")
def show_delete_course_confirmation_dialog(course):
    st.markdown(f"Are you sure you want to delete the course: `{course['name']}`?")
    (
        confirm_col,
        cancel_col,
    ) = st.columns([1.5, 6])

    if confirm_col.button("Confirm", type="primary"):
        delete_course(course["id"])
        refresh_courses()

        # invalidate cache
        clear_course_cache_for_cohorts(course["cohorts"])

        set_toast("Course deleted successfully!")
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


def update_task_order(current_order, updated_order, milestone_tasks):
    selected_task = milestone_tasks[current_order]

    # task ordering in milestones are likely to not be in a sequence
    # so, to update the ordering, instead of adding/subtracting 1 from the ordering of all tasks,
    # for each task between the current and updated order, we assign the ordering values
    if current_order < updated_order:
        task_indices_to_update = range(current_order + 1, updated_order + 1)
        update_value = -1
    else:
        task_indices_to_update = range(updated_order, current_order)
        update_value = 1

    task_orders_to_update = [
        (
            milestone_tasks[task_index + update_value]["ordering"],
            milestone_tasks[task_index]["course_task_id"],
        )
        for task_index in task_indices_to_update
    ]
    task_orders_to_update.append(
        (
            milestone_tasks[updated_order]["ordering"],
            selected_task["course_task_id"],
        )
    )
    update_task_orders_in_db(task_orders_to_update)


@st.dialog("Update Task Order")
def show_update_task_order_dialog(current_order: int, milestone_tasks: List[Dict]):
    st.write(f"Current Order: `{current_order + 1}`")

    with st.form("update_task_order_form", border=False):
        updated_order = st.selectbox(
            "Enter new order",
            options=list(range(1, len(milestone_tasks) + 1)),
            index=current_order,
        )
        if st.form_submit_button("Update", type="primary", use_container_width=True):
            if updated_order == current_order + 1:
                st.error("No changes made")
                return

            update_task_order(current_order, updated_order - 1, milestone_tasks)
            set_toast("Task order updated successfully!")
            st.rerun()


def show_course_tasks_tab(selected_course):
    st.subheader("Tasks")
    if not selected_course["tasks"]:
        st.info("This course has no tasks yet")
        return

    cols = st.columns([1, 2])
    with cols[0]:
        milestone = st.selectbox(
            "Filter by milestone",
            set([task["milestone"] for task in selected_course["tasks"]]),
            key="course_task_milestone_filter",
        )

    filtered_tasks = [
        task for task in selected_course["tasks"] if task["milestone"] == milestone
    ]

    filtered_df = pd.DataFrame(
        filtered_tasks,
        columns=["id", "verified", "name", "type", "response_type", "coding_language"],
    )

    action_container = st.container()

    event = st.dataframe(
        filtered_df,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        use_container_width=True,
        column_config={
            "id": None,
            "verified": st.column_config.CheckboxColumn(
                default=False,
                width="small",
            ),
            "name": st.column_config.TextColumn(width="large"),
        },
    )

    if len(event.selection["rows"]):
        index = event.selection["rows"][0]
        action_container.button(
            "Update order",
            on_click=show_update_task_order_dialog,
            args=(index, filtered_tasks),
        )


def show_course_cohorts(selected_course):
    cols = st.columns([1, 0.4])
    with cols[0]:
        if not selected_course["cohorts"]:
            st.markdown("#### Cohorts")
            st.info("This course has not been added to any cohort yet")
            cols[1].container(height=40, border=False)
        else:
            # st.write(selected_course["cohorts"])
            st.pills(
                "Cohorts",
                selected_course["cohorts"],
                format_func=lambda x: x["name"],
                disabled=True,
            )
            cols[1].container(height=5, border=False)

    if cols[1].button("Update", key="update_course_cohorts"):
        show_update_course_cohorts_dialog(
            selected_course["id"], selected_course["cohorts"]
        )


def update_course_name(course, new_name):
    if new_name == course["name"]:
        st.toast("No changes made")
        return

    update_course_name_in_db(course["id"], new_name)
    refresh_courses()

    # invalidate cache
    clear_course_cache_for_cohorts(course["cohorts"])

    set_toast("Course name updated successfully!")
    st.rerun()


def show_course_name_update_form(selected_course):
    with st.form("update_course_name_form", border=False):
        cols = st.columns([1, 0.4])
        updated_course_name = cols[0].text_input(
            "Course Name", value=selected_course["name"]
        )
        cols[1].container(height=10, border=False)
        if cols[1].form_submit_button("Update"):
            update_course_name(selected_course, updated_course_name)


def show_courses_tab():
    cols = st.columns([1.2, 0.5, 0.55, 2.5])

    selected_course = cols[0].selectbox(
        "Select a course",
        st.session_state.courses,
        format_func=lambda course: course["name"],
    )

    cols[1].container(height=10, border=False)
    if cols[1].button("Create Course", type="primary"):
        show_create_course_dialog()

    if not len(st.session_state.courses):
        st.error("No courses added yet")
        return

    if not selected_course:
        return

    selected_course["tasks"] = get_tasks_for_course(selected_course["id"])
    selected_course["cohorts"] = get_cohorts_for_course(selected_course["id"])

    st.divider()

    main_tab_cols = st.columns([0.4, 0.05, 1])

    with main_tab_cols[0]:
        show_course_name_update_form(selected_course)
        show_course_cohorts(selected_course)

        st.container(height=10, border=False)
        if st.button("Delete Course", icon="🗑️"):
            show_delete_course_confirmation_dialog(selected_course)

    with main_tab_cols[-1]:
        show_course_tasks_tab(selected_course)


with tabs[1]:
    show_courses_tab()


def add_milestone(new_milestone, milestone_color):
    if not new_milestone:
        st.toast("Enter a milestone name")
        return

    if new_milestone in [
        milestone["name"] for milestone in st.session_state.milestones
    ]:
        st.toast("Milestone already exists")
        return

    insert_milestone_to_db(new_milestone, milestone_color, st.session_state.org_id)
    st.toast("New milestone added")
    refresh_milestones()

    st.session_state.new_milestone = ""


def delete_milestone(milestone):
    delete_milestone_from_db(milestone["id"])
    set_toast("Milestone deleted")
    refresh_milestones()


@st.dialog("Delete Milestone")
def show_milestone_delete_confirmation_dialog(milestone):
    st.markdown(f"Are you sure you want to delete `{milestone['name']}`?")
    (
        confirm_col,
        cancel_col,
        _,
    ) = st.columns([1, 2, 4])

    if confirm_col.button("Yes", type="primary"):
        delete_milestone(milestone)
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


def update_milestone_color(milestone_id, milestone_color):
    update_milestone_color_in_db(milestone_id, milestone_color)
    st.toast("Milestone color updated")
    refresh_milestones()


def show_milestones_tab():
    cols = st.columns([1, 0.15, 1, 1])
    new_milestone = cols[0].text_input(
        "Enter milestone and press `Enter`", key="new_milestone"
    )

    if "new_milestone_color" not in st.session_state:
        st.session_state.new_milestone_color = generate_random_color()

    if new_milestone:
        cols[1].container(height=10, border=False)
        milestone_color = cols[1].color_picker(
            "Pick A Color",
            key="new_milestone_color",
            label_visibility="collapsed",
        )
        cols[2].container(height=10, border=False)
        cols[2].button(
            "Add Milestone",
            on_click=add_milestone,
            args=(
                new_milestone,
                milestone_color,
            ),
            key="add_milestone",
        )

    if not st.session_state.milestones:
        st.info("No milestones added yet")
        return

    num_layout_cols = 3
    layout_cols = st.columns(num_layout_cols)
    for i, milestone in enumerate(st.session_state.milestones):
        with layout_cols[i % num_layout_cols].container(
            border=True,
        ):
            cols = st.columns([1, 2.5, 1.5, 1.5])
            milestone_name = f'<div style="margin-top: 0px;">{milestone["name"]}</div>'
            milestone_color = cols[0].color_picker(
                "Pick A Color",
                milestone["color"],
                key=f'color_picker_{milestone["id"]}',
                label_visibility="collapsed",
                # disabled=True,
            )
            cols[1].markdown(milestone_name, unsafe_allow_html=True)

            if milestone_color != milestone["color"]:
                cols[2].button(
                    "Update",
                    on_click=update_milestone_color,
                    args=(milestone["id"], milestone_color),
                    key=f"update_milestone_color_{i}",
                    type="primary",
                )

            cols[-1].button(
                "Delete",
                on_click=show_milestone_delete_confirmation_dialog,
                args=(milestone,),
                key=f"delete_milestone_{i}",
            )


with tabs[3]:
    show_milestones_tab()


def add_tag(new_tag):
    if not new_tag:
        st.toast("Enter a tag name")
        return

    if new_tag in [tag["name"] for tag in st.session_state.tags]:
        st.toast("Tag already exists")
        return

    # since we show the tags in reverse order, we need to save them in reverse order
    create_tag_in_db(new_tag, st.session_state.org_id)
    st.toast("New tag added")
    refresh_tags()

    st.session_state.new_tag = ""


def delete_tag(tag):
    delete_tag_from_db(tag["id"])
    set_toast("Tag deleted")
    refresh_tags()


@st.dialog("Delete Tag")
def show_tag_delete_confirmation_dialog(tag):
    st.markdown(f"Are you sure you want to delete `{tag['name']}`?")
    (
        confirm_col,
        cancel_col,
        _,
    ) = st.columns([1, 2, 4])

    if confirm_col.button("Yes", type="primary"):
        delete_tag(tag)
        st.rerun()

    if cancel_col.button("Cancel"):
        st.rerun()


def show_tags_tab():
    cols = st.columns(4)
    new_tag = cols[0].text_input("Enter Tag", key="new_tag")
    cols[1].container(height=10, border=False)
    cols[1].button(
        "Add",
        on_click=add_tag,
        args=(new_tag,),
        key="add_tag",
    )

    if not st.session_state.tags:
        st.info("No tags added yet")
        return

    num_layout_cols = 3
    layout_cols = st.columns(num_layout_cols)
    for i, tag in enumerate(st.session_state.tags[::-1]):
        with layout_cols[i % num_layout_cols].container(
            border=True,
        ):
            cols = st.columns([3, 1])
            cols[0].write(tag["name"])
            cols[-1].button(
                "Delete",
                on_click=show_tag_delete_confirmation_dialog,
                args=(tag,),
                key=f"delete_tag_{i}",
            )


with tabs[4]:
    show_tags_tab()


def show_analytics_tab():
    cols = st.columns(4)
    selected_module = cols[0].selectbox("Select a module", ["CV Review"])

    if selected_module != "CV Review":
        st.error("Analytics for this module not implemented yet")
        return

    all_cv_review_usage = get_all_cv_review_usage()
    df = pd.DataFrame(all_cv_review_usage)

    if not len(df):
        st.info("No usage data yet!")
        return

    # Get unique emails for filtering
    unique_emails = df["user_email"].unique().tolist()
    selected_email = cols[1].selectbox(
        "Select specific user", unique_emails, index=None
    )

    # Filter usage counts for selected email if one is chosen
    if selected_email:
        user_entries = df[df["user_email"] == selected_email].reset_index(drop=True)

        st.markdown("#### Submissions")
        # Convert ai_review string to dict and extract timestamp
        user_entries = user_entries.sort_values("created_at", ascending=False)

        for index, entry in user_entries.iterrows():
            with st.expander(
                f"#{index + 1} - {entry['role']} ({datetime.fromisoformat(entry['created_at']).strftime('%B %d, %Y - %I:%M %p')})"
            ):
                df = pd.DataFrame(
                    json.loads(entry["ai_review"]), columns=["Category", "Feedback"]
                )
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.markdown("#### Overview")
        # Group by user email and get counts
        # Get submission counts
        usage_counts = (
            df.groupby("user_email").size().reset_index(name="number of submissions")
        )

        # Get unique roles per user
        roles_by_user = (
            df.groupby("user_email")["role"]
            .agg(lambda x: ", ".join(sorted(set(x))))
            .reset_index(name="rolesr")
        )

        # Merge the two dataframes
        usage_stats = usage_counts.merge(roles_by_user, on="user_email")
        st.dataframe(usage_stats, use_container_width=True, hide_index=True)


if is_hva_org:
    with tabs[5]:
        show_analytics_tab()


@st.dialog("Add Member")
def show_add_member_dialog(org_users):
    with st.form("add_member_form", border=False):
        member_email = st.text_input("Enter email")
        role = st.selectbox("Select role", ["admin"], disabled=True)

        submit_button = st.form_submit_button(
            "Add Member",
            use_container_width=True,
            type="primary",
        )
        if submit_button:
            try:
                # Check that the email address is valid
                member_email = validate_email(member_email)
                if member_email.normalized in [user["email"] for user in org_users]:
                    st.error("Member already exists")
                    return

                add_user_to_org_by_email(
                    member_email.normalized, st.session_state.org_id, role
                )
                set_toast("Member added successfully")
                st.rerun()
            except EmailNotValidError as e:
                # The exception message is human-readable explanation of why it's
                # not a valid (or deliverable) email address.
                st.error("Invalid email")


def show_settings_tab():
    st.markdown("#### Members")

    org_users = get_org_users(st.session_state.org_id)
    st.button("Add Member", on_click=show_add_member_dialog, args=(org_users,))

    df = pd.DataFrame(org_users)
    st.dataframe(
        df, use_container_width=True, hide_index=True, column_order=["email", "role"]
    )


with tabs[-1]:
    show_settings_tab()
