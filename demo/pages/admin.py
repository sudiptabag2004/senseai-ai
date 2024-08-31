import traceback
import asyncio
import sys
import os
import streamlit as st
import pandas as pd
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# root_dir = os.path.dirname(os.path.abspath(__file__))

# if root_dir not in sys.path:
#     sys.path.append(root_dir)

from lib.llm import get_llm_input_messages, call_llm_and_parse_output, COMMON_INSTRUCTIONS
from lib.utils import load_json, save_json
from lib.init import init_env_vars
from lib.config import tasks_db_path

init_env_vars()

if 'tasks' not in st.session_state:
    st.session_state.tasks = load_json(tasks_db_path)

model = st.selectbox('Model', [{'label': 'gpt-4o', 'version': 'gpt-4o-2024-08-06'}, {'label': 'gpt-4o-mini', 'version': 'gpt-4o-mini-2024-07-18'}], format_func=lambda val: val['label'])

@st.spinner('Generating answer...')
def generate_answer():
    system_prompt_template = """You are a helpful and encouraging tutor.\n\nYou will be given a task that has been assigned to a student along with its description.
        \n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructons:\n- Give some reasoning before arriving at the answer but keep it concise.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name: {task_name}\n\nTask description: {task_description}"""

    class Output(BaseModel):
        solution: str = Field(
            title="solution",
            description="The solution to the task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=st.session_state.task_name,
        task_description=st.session_state.task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS
    )

    try:
        pred_dict = asyncio.run(call_llm_and_parse_output(
            llm_input_messages,
            model=model['version'],
            output_parser=output_parser,
            max_tokens=2048,
            verbose=True,
            # labels=["final_answers", "audit rights"],
            # model_type=model_type,
        ))
        st.session_state.answer = pred_dict['solution']
    except Exception as exception:
        traceback.print_exc()
        raise Exception

    

tag_list = ['Functions', 'Javascript']

def update_task_json():
    save_json(tasks_local_path, st.session_state.tasks)

def add_task_to_list():
    st.session_state.tasks.append({'name': st.session_state.task_name, 'description': st.session_state.task_description, 'answer': st.session_state.answer, 'tags': st.session_state.tags, 'generation_model': model['version'], 'verified': True})
    update_task_json()

@st.dialog("Add a new task")
def show_task_form():
    task_name = st.text_input("Name", key='task_name', value='Greet function')
    task_description = st.text_area("Description", key='task_description', value="""Define a function called greet that takes a name as an argument and returns a greeting message. For example, if the name is "Alice", the function should return "Hello, Alice!".
Call the greet function you defined in the previous task with your name as the argument and log the result to the console.
Modify the greet function to have a default argument of "Guest" for the name parameter. This means that if no name is provided, the function should return "Hello, Guest!".
Rewrite the greet function as a function expression and store it in a variable called greetFunction.
Rewrite the greet function as an arrow function.""")

    st.multiselect("Tags", tag_list, key='tags', default=tag_list)

    answer = st.text_area("Answer", key='answer')
    generate_answer_col, _, verify_col = st.columns(3)

    generate_answer_col.button("Generate answer", on_click=generate_answer, disabled=(not task_description or not task_name or answer != ""))
    
    # st.spinner('Generating answer...', visible=st.session_state.is_answer_generation_in_progress)

    if answer and verify_col.button("Verify and Add", on_click=add_task_to_list):
        # st.session_state.vote = {"item": item, "reason": reason}
        st.rerun()


def delete_tasks_from_list(task_indices):
    st.session_state.tasks = [st.session_state.tasks[i] for i in range(len(st.session_state.tasks)) if i not in task_indices]
    update_task_json()
    st.rerun()

@st.dialog("Delete tasks")
def delete_tasks(task_indices):
    st.write('Are you sure you want to delete the selected tasks?')

    confirm_col, cancel_col, _, _ = st.columns([1,1,2,2])
    if confirm_col.button('Yes', use_container_width=True):
        st.session_state.tasks = [st.session_state.tasks[i] for i in range(len(st.session_state.tasks)) if i not in event.selection['rows']]
        st.rerun()
    
    if cancel_col.button('No', use_container_width=True, type='primary'):
        st.rerun()


add_task = st.button('Add a new task')
if add_task:
    show_task_form()


st.write('## Tasks')

if not st.session_state.tasks:
    st.error('No tasks added yet')
    st.stop()

df = pd.DataFrame(st.session_state.tasks)

df_actions = st.container()

event = st.dataframe(
    df,
    on_select='rerun',
    selection_mode='multi-row',
    use_container_width=True
)


if len(event.selection['rows']):
    if df_actions.button('Delete selected tasks'):
        delete_tasks(event.selection['rows'])