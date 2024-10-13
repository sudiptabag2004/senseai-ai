from typing import List, Dict
import itertools
import traceback
import asyncio
from functools import partial
import numpy as np
import streamlit as st

st.set_page_config(layout="wide")

from copy import deepcopy
import pandas as pd
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# root_dir = os.path.dirname(os.path.abspath(__file__))

# if root_dir not in sys.path:
#     sys.path.append(root_dir)

from lib.llm import (
    get_llm_input_messages,
    call_llm_and_parse_output,
    COMMON_INSTRUCTIONS,
)
from lib.init import init_env_vars, init_db
from lib.db import (
    get_all_tasks,
    store_task as store_task_to_db,
    delete_tasks as delete_tasks_from_db,
    update_task as update_task_in_db,
    update_column_for_task_ids,
    update_tests_for_task,
)
from lib.strings import *
from lib.utils import load_json, save_json
from lib.config import coding_languages_supported

init_env_vars()
init_db()

if "tasks" not in st.session_state:
    st.session_state.tasks = get_all_tasks()


if "tests" not in st.session_state:
    st.session_state.tests = []

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = ""

if "final_answer" not in st.session_state:
    st.session_state.final_answer = ""

if "show_toast" not in st.session_state:
    st.session_state.show_toast = False

if "toast_message" not in st.session_state:
    st.session_state.toast_message = ""

if st.session_state.show_toast:
    st.toast(st.session_state.toast_message)
    st.session_state.show_toast = False

model = st.selectbox(
    "Model",
    [
        {"label": "gpt-4o", "version": "gpt-4o-2024-08-06"},
        {"label": "gpt-4o-mini", "version": "gpt-4o-mini-2024-07-18"},
    ],
    format_func=lambda val: val["label"],
)


async def generate_answer_for_task(task_name, task_description):
    system_prompt_template = """You are a helpful and encouraging tutor.\n\nYou will be given a task that has been assigned to a student along with its description.\n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

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
            verbose=True,
            # labels=["final_answers", "audit rights"],
            # model_type=model_type,
        )
        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()
        raise Exception


@st.spinner("Generating answer...")
def generate_answer_for_form_task():
    st.session_state.ai_answer = asyncio.run(
        generate_answer_for_task(
            st.session_state.task_name, st.session_state.task_description
        )
    )


tag_list_path = "./lib/tags.json"
tag_list = load_json(tag_list_path)


def get_task_type(is_code_editor_enabled: bool):
    if is_code_editor_enabled:
        return "coding"

    return "text"


def convert_tests_to_prompt(tests: List[Dict]) -> str:
    if not tests:
        return ""

    return "\n-----------------\n".join(
        [f"Input:\n{test['input']}\n\nOutput:\n{test['output']}" for test in tests]
    )


async def generate_tests_for_task_from_llm(task_name, task_description, tests):
    system_prompt_template = """You are a test case generator for programming tasks.\n\nYou will be given a task name and its description, optionally along with a list of test cases.\n\nYou need to generate a list of test cases in the form of input/output pairs.\n\n- Give some reasoning before arriving at the answer but keep it concise.\n- Create diverse test cases that cover various scenarios, including edge cases.\n- Ensure the test cases are relevant to the task description.\n- Provide at least 3 test cases, but no more than 5.\n- Ensure that every test case is unique.\n- If you are given a list of test cases, you need to ensure that the new test cases you generate are not duplicates of the ones in the list.\n{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name: {task_name}\n\nTask description: {task_description}\n\nTest cases:\n\n{tests}"""

    class TestCase(BaseModel):
        input: str = Field(description="The input for the test case")
        output: str = Field(description="The expected output for the test case")
        description: str = Field(
            description="A very brief description of the test case", default=""
        )

    class Output(BaseModel):
        test_cases: List[TestCase] = Field(
            description="A list of test cases for the given task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
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
    task_name: str, task_description: str, tests: List[Dict]
):
    with st.spinner("Generating tests..."):
        generated_tests = await generate_tests_for_task_from_llm(
            task_name,
            task_description,
            tests,
        )

    st.session_state.tests.extend(generated_tests)


def delete_test_from_session_state(test_index):
    st.session_state.tests.pop(test_index)


def update_test_in_session_state(test_index):
    st.session_state.tests[test_index] = {
        "input": st.session_state[f"test_input_{test_index}"],
        "output": st.session_state[f"test_output_{test_index}"],
        "description": st.session_state[f"test_description_{test_index}"],
    }


def add_verified_task_to_list(final_answer):
    task_type = get_task_type(st.session_state.show_code_editor)

    store_task_to_db(
        st.session_state.task_name,
        st.session_state.task_description,
        final_answer,
        st.session_state.tags,
        task_type,
        st.session_state.coding_languages,
        model["version"],
        True,
        st.session_state.tests,  # Add this line to include the tests
    )
    st.session_state.tasks = get_all_tasks()


def add_tests_to_task(task_name: str, task_description: str):
    cols = st.columns([3.5, 1])
    cols[0].subheader(admin_code_test_cases_label)
    if cols[1].button("Generate", key="generate_tests"):
        asyncio.run(
            generate_tests_for_task(task_name, task_description, st.session_state.tests)
        )

    for test_index, test in enumerate(st.session_state.tests):
        with st.expander(f"Test {test_index + 1}"):
            st.text_area(
                label="Input",
                value=test["input"],
                key=f"test_input_{test_index}",
                on_change=update_test_in_session_state,
                args=(test_index,),
            )
            st.text_area(
                label="Output",
                value=test["output"],
                key=f"test_output_{test_index}",
                on_change=update_test_in_session_state,
                args=(test_index,),
            )
            st.text_area(
                label="Description (optional)",
                value=test.get("description", ""),
                key=f"test_description_{test_index}",
                on_change=update_test_in_session_state,
                args=(test_index,),
            )
            cols = st.columns([3, 1.1, 1])
            cols[-1].button(
                "Delete",
                type="primary",
                on_click=delete_test_from_session_state,
                args=(test_index,),
                key=f"delete_test_{test_index}",
            )
            # TODO: add support for deleting tests

    st.text_area("Input", key="test_input")
    st.text_area("Output", key="test_output")
    st.text_area("Description (optional)", key="test_description")

    def add_test():
        st.session_state.tests.append(
            {
                "input": st.session_state.test_input,
                "output": st.session_state.test_output,
                "description": st.session_state.test_description,
            }
        )
        st.session_state.test_input = ""
        st.session_state.test_output = ""
        st.session_state.test_description = ""

    st.button("Add Test", on_click=add_test)

    # st.session_state.tests


@st.dialog("Edit tests for task")
def edit_tests_for_task(task_id):
    task_details = df[df["id"] == task_id].iloc[0]
    if not st.session_state.tests:
        st.session_state.tests = deepcopy(task_details["tests"])

    add_tests_to_task(
        task_details["name"],
        task_details["description"],
    )

    if st.button(
        "Update tests",
        type="primary",
        use_container_width=True,
        disabled=task_details["tests"] == st.session_state.tests,
        help=(
            "Nothing to update"
            if task_details["tests"] == st.session_state.tests
            else ""
        ),
    ):
        update_tests_for_task(task_id, st.session_state.tests)
        st.session_state.tasks = get_all_tasks()
        st.session_state.show_toast = True
        st.session_state.toast_message = "Tests updated successfully!"
        st.session_state.tests = []
        st.rerun()


@st.dialog("Add a new task")
def show_task_form():
    st.text_input("Name", key="task_name", value="Greet function")
    st.text_area(
        "Description",
        key="task_description",
        value="""Write a python code to take user input and display it.""",
    )

    st.multiselect(
        "Tags", tag_list, key="tags", default=[tag_list[tag_list.index("Python")]]
    )

    with st.expander("Add new tags"):
        cols = st.columns([3, 1])
        cols[0].text_input("New tag", key="new_tag")
        cols[1].markdown("###")
        if cols[1].button("Add Tag"):
            if st.session_state.new_tag in tag_list:
                st.error("Tag already exists")
            else:
                tag_list.append(st.session_state.new_tag)
                save_json(tag_list_path, tag_list)
                st.rerun()

    cols = st.columns(2)

    if cols[0].checkbox(
        admin_show_code_editor_label,
        value=True,
        help=admin_show_code_editor_help,
        key="show_code_editor",
    ):
        if (
            "coding_languages" in st.session_state
            and st.session_state.coding_languages is None
        ):
            st.session_state.coding_languages = []
        st.multiselect(
            admin_code_editor_language_label,
            coding_languages_supported,
            help=admin_code_editor_language_help,
            key="coding_languages",
            default=["Python"],
        )
        # st.session_state.coding_languages
    else:
        st.session_state.coding_languages = None

    # test cases
    if st.session_state.show_code_editor and st.checkbox("I want to add tests", True):
        add_tests_to_task(
            st.session_state.task_name,
            st.session_state.task_description,
        )

    st.subheader("Answer")
    cols = st.columns([3.5, 1])

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
        label_visibility="collapsed",
    )
    if not final_answer and st.session_state.ai_answer:
        final_answer = st.session_state.ai_answer

    if final_answer and st.button(
        "Verify and Add",
        on_click=add_verified_task_to_list,
        args=(final_answer,),
        use_container_width=True,
        type="primary",
    ):
        # st.session_state.vote = {"item": item, "reason": reason}
        st.session_state.tests = []
        st.rerun()


single_task_col, bulk_upload_tasks_col, _, _ = st.columns([1, 3, 2, 2])

add_task = single_task_col.button("Add a new task")
bulk_upload_tasks = bulk_upload_tasks_col.button("Bulk upload tasks")

if add_task:
    st.session_state.tests = []
    st.session_state.ai_answer = ""
    st.session_state.final_answer = ""
    show_task_form()


async def generate_answer_for_bulk_task(task_id, task_name, task_description):
    answer = await generate_answer_for_task(task_name, task_description)
    return task_id, answer


def update_progress_bar(progress_bar, count, num_tasks, message):
    progress_bar.progress(count / num_tasks, text=f"{message} ({count}/{num_tasks})")


async def generate_answers_for_tasks(tasks_df):
    coroutines = []

    for index, row in tasks_df.iterrows():
        coroutines.append(
            generate_answer_for_bulk_task(index, row["Name"], row["Description"])
        )

    num_tasks = len(tasks_df)
    progress_bar = st.progress(
        0, text=f"Generating answers for tasks... (0/{num_tasks})"
    )

    # for i, answer in enumerate(await tqdm_asyncio.gather(*coroutines)):
    #     print(i, answer)

    count = 0

    tasks_df["Answer"] = [None] * num_tasks

    for completed_task in asyncio.as_completed(coroutines):
        task_id, answer = await completed_task
        tasks_df.at[task_id, "Answer"] = answer
        count += 1

        update_progress_bar(
            progress_bar, count, num_tasks, "Generating answers for tasks..."
        )
        # print('done', result)

    progress_bar.empty()

    return tasks_df


@st.dialog("Bulk upload tasks")
def show_bulk_upload_tasks_form():
    show_code_editor = st.checkbox(
        admin_show_code_editor_label, value=True, help=admin_show_code_editor_help
    )
    coding_languages = None

    if show_code_editor:
        coding_languages = st.multiselect(
            admin_code_editor_language_label,
            coding_languages_supported,
            help=admin_code_editor_language_help,
            key="coding_languages",
        )

    task_type = get_task_type(show_code_editor)

    uploaded_file = st.file_uploader(
        "Choose a CSV file with the columns:\n\n`Name`, `Description`, `Tags`, `Answer` (optional)",
        type="csv",
    )

    if uploaded_file:
        tasks_df = pd.read_csv(uploaded_file)

        if "Answer" not in tasks_df.columns:
            tasks_df = asyncio.run(generate_answers_for_tasks(tasks_df))

            # st.write(row)
            # my_bar.progress(index + 1, text="Generating answers for tasks... ({}/{})".format(index + 1, len(tasks_df)))
            # time.sleep(0.1)

        # st.dataframe(tasks_df)

        for _, row in tasks_df.iterrows():
            store_task_to_db(
                row["Name"],
                row["Description"],
                row["Answer"],
                row["Tags"].split(","),
                task_type,
                coding_languages,
                model["version"],
                False,
            )

        # st.success("Answers generated successfully. Select 'Verify Mode', go through the unverified answers and verify them for learners to access them.")

        st.session_state.tasks = get_all_tasks()
        st.rerun()

        # if st.button("Got it!"):
        #     st.rerun()

        # st.write(dataframe)
        # st.success("File uploaded successfully")


if bulk_upload_tasks:
    show_bulk_upload_tasks_form()


def delete_tasks_from_list(task_ids):
    delete_tasks_from_db(task_ids)
    st.session_state.tasks = get_all_tasks()
    st.rerun()


@st.dialog("Delete tasks")
def show_delete_confirmation(task_ids):
    st.write("Are you sure you want to delete the selected tasks?")

    confirm_col, cancel_col, _, _ = st.columns([1, 1, 2, 2])
    if confirm_col.button("Yes", use_container_width=True):
        delete_tasks_from_list(task_ids)
        st.rerun()

    if cancel_col.button("No", use_container_width=True, type="primary"):
        st.rerun()


def update_tasks_with_new_value(
    task_ids: List[int], column_to_update: str, new_value: str
):
    update_column_for_task_ids(task_ids, column_to_update, new_value)
    st.session_state.tasks = get_all_tasks()
    st.rerun()


@st.dialog("Edit tasks")
def show_task_edit_dialog(task_ids):
    column_to_update = st.selectbox(
        "Select a column to update", ["type", "coding_language"]
    )
    if column_to_update == "type":
        option_component = st.selectbox
        options = ["text", "coding"]
    else:
        option_component = st.multiselect
        options = coding_languages_supported

    new_value = option_component("Select the new value", options)

    st.write("Are you sure you want to update the selected tasks?")

    confirm_col, cancel_col, _, _ = st.columns([1, 1, 2, 2])
    if confirm_col.button("Yes", use_container_width=True):
        update_tasks_with_new_value(task_ids, column_to_update, new_value)
        st.rerun()

    if cancel_col.button("No", use_container_width=True, type="primary"):
        st.rerun()


tasks_heading = "## Tasks"
tasks_description = ""

num_tasks = len(st.session_state.tasks)

if num_tasks > 0:
    tasks_heading = f"## Tasks ({num_tasks})"
    tasks_description = f"You can select multiple tasks by clicking beside the `id` column of each task and do any of the following\n\n- Delete tasks\n\n- Edit task attributes in bulk (e.g. task type, whether to show code preview, coding language)\n\nYou can also go through the unverified answers and verify them for learners to access them by selecting `Edit Mode`."

st.write(tasks_heading)
with st.expander("Learn more"):
    st.write(tasks_description)

edit_mode_col, save_col, _, _, _ = st.columns([2, 3, 1, 1, 1])

is_edit_mode = edit_mode_col.checkbox(
    "Edit Mode",
    value=False,
    help="Select this to go through the unverified answers and verify them for learners to access them or make any other changes to the tasks.",
)

if not st.session_state.tasks:
    st.error("No tasks added yet")
    st.stop()

df = pd.DataFrame(st.session_state.tasks)
df["coding_language"] = df["coding_language"].apply(
    lambda x: x.split(",") if isinstance(x, str) else x
)

all_tags = np.unique(
    list(itertools.chain(*[tags for tags in df["tags"].tolist()]))
).tolist()
filter_tags = st.multiselect("Filter by tags", all_tags)

if filter_tags:
    df = df[df["tags"].apply(lambda x: any(tag in x for tag in filter_tags))]

column_config = {
    # 'id': None
    "description": st.column_config.TextColumn(width="medium"),
    "answer": st.column_config.TextColumn(width="medium"),
}

column_order = [
    "id",
    "verified",
    "name",
    "description",
    "answer",
    "tags",
    "type",
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
            row["tags"],
            row["type"],
            row["coding_language"],
            row["generation_model"],
            row["verified"],
        )

    # Refresh the tasks in the session state
    st.session_state.tasks = get_all_tasks()
    st.toast("Changes saved successfully!")
    # st.rerun()


if not is_edit_mode:
    delete_col, edit_col, add_tests_col, _ = st.columns([1.5, 2, 4, 7])

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
        if delete_col.button("Delete tasks"):
            # import ipdb; ipdb.set_trace()
            show_delete_confirmation(task_ids)

        if edit_col.button("Edit task attributes"):
            # import ipdb; ipdb.set_trace()
            show_task_edit_dialog(task_ids)

        if add_tests_col.button("Add/Edit tests"):
            if len(task_ids) == 1:
                edit_tests_for_task(task_ids[0])
            else:
                st.error("Please select only one task to edit tests for.")

else:
    edited_df = st.data_editor(
        df,
        hide_index=True,
        column_config=column_config,
        column_order=column_order,
        use_container_width=True,
    )

    if not df.equals(edited_df):
        save_col.button(
            "Save changes",
            type="primary",
            on_click=partial(save_changes_in_edit_mode, edited_df),
        )
