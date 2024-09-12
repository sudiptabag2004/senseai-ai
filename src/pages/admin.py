import traceback
import asyncio
from functools import partial
import streamlit as st
import pandas as pd
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from tqdm.asyncio import tqdm_asyncio

# root_dir = os.path.dirname(os.path.abspath(__file__))

# if root_dir not in sys.path:
#     sys.path.append(root_dir)

from lib.llm import get_llm_input_messages, call_llm_and_parse_output, COMMON_INSTRUCTIONS
from lib.init import init_env_vars, init_db
from lib.db import get_all_tasks, store_task as store_task_to_db, delete_tasks as delete_tasks_from_db, update_task as update_task_in_db

init_env_vars()

init_db()

if 'tasks' not in st.session_state:
    st.session_state.tasks = get_all_tasks()


model = st.selectbox('Model', [{'label': 'gpt-4o', 'version': 'gpt-4o-2024-08-06'}, {'label': 'gpt-4o-mini', 'version': 'gpt-4o-mini-2024-07-18'}], format_func=lambda val: val['label'])

async def generate_answer_for_task(task_name, task_description):
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
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model['version'],
            output_parser=output_parser,
            max_tokens=2048,
            verbose=True,
            # labels=["final_answers", "audit rights"],
            # model_type=model_type,
        )
        return pred_dict['solution']
    except Exception as exception:
        traceback.print_exc()
        raise Exception


@st.spinner('Generating answer...')
def generate_answer_for_form_task():
    st.session_state.answer = asyncio.run(generate_answer_for_task(st.session_state.task_name, st.session_state.task_description))


tag_list = ['Functions', 'Javascript']


def add_verified_task_to_list():
    store_task_to_db(st.session_state.task_name, st.session_state.task_description, st.session_state.answer, st.session_state.tags, model['version'], True)
    st.session_state.tasks = get_all_tasks()

@st.dialog("Add a new task")
def show_task_form():
    # st.session_state.answer = ""

    task_name = st.text_input("Name", key='task_name', value='Greet function')
    task_description = st.text_area("Description", key='task_description', value="""Define a function called greet that takes a name as an argument and returns a greeting message. For example, if the name is "Alice", the function should return "Hello, Alice!".
Call the greet function you defined in the previous task with your name as the argument and log the result to the console.
Modify the greet function to have a default argument of "Guest" for the name parameter. This means that if no name is provided, the function should return "Hello, Guest!".
Rewrite the greet function as a function expression and store it in a variable called greetFunction.
Rewrite the greet function as an arrow function.""")

    st.multiselect("Tags", tag_list, key='tags', default=tag_list)

    answer = st.text_area("Answer", key='answer')
    generate_answer_col, _, verify_col = st.columns(3)

    generate_answer_col.button("Generate answer", on_click=generate_answer_for_form_task, disabled=(not task_description or not task_name or answer != ""))
    
    # st.spinner('Generating answer...', visible=st.session_state.is_answer_generation_in_progress)

    if answer and verify_col.button("Verify and Add", on_click=add_verified_task_to_list):
        # st.session_state.vote = {"item": item, "reason": reason}
        st.rerun()
    
    # # reset answer
    # st.session_state.answer = None


single_task_col, bulk_upload_tasks_col, _, _ = st.columns([1, 2, 1, 1])

add_task = single_task_col.button('Add a new task')
bulk_upload_tasks = bulk_upload_tasks_col.button('Bulk upload tasks')

if add_task:
    show_task_form()


async def generate_answer_for_bulk_task(task_id, task_name, task_description):
    answer = await generate_answer_for_task(task_name, task_description)
    return task_id, answer

def update_progress_bar(progress_bar, count, num_tasks):
    progress_bar.progress(count / num_tasks, text=f"Generating answers for tasks... ({count}/{num_tasks})")

async def generate_answers_for_tasks(tasks_df):
    coroutines = []

    for index, row in tasks_df.iterrows():
        coroutines.append(generate_answer_for_bulk_task(index, row['Name'], row['Description']))

    num_tasks = len(tasks_df)
    progress_bar = st.progress(0, text=f"Generating answers for tasks... (0/{num_tasks})")

    # for i, answer in enumerate(await tqdm_asyncio.gather(*coroutines)):
    #     print(i, answer)

    count = 0

    tasks_df['Answer'] = [None] * num_tasks

    for completed_task in asyncio.as_completed(coroutines):
        task_id, answer = await completed_task
        tasks_df.at[task_id, 'Answer'] = answer
        count += 1

        update_progress_bar(progress_bar, count, num_tasks)
        # print('done', result)

    progress_bar.empty()

    return tasks_df

@st.dialog("Bulk upload tasks")
def show_bulk_upload_tasks_form():
    uploaded_file = st.file_uploader("Choose a CSV file with columns: `Name`, `Description`, `Tags`", type='csv')
    if uploaded_file:
        tasks_df = pd.read_csv(uploaded_file)    

        # with st.spinner("Generating answers for tasks..."):
        tasks_df = asyncio.run(generate_answers_for_tasks(tasks_df))

            # st.write(row)
            # my_bar.progress(index + 1, text="Generating answers for tasks... ({}/{})".format(index + 1, len(tasks_df)))
            # time.sleep(0.1)

        # st.dataframe(tasks_df)
        
        for _, row in tasks_df.iterrows():
            store_task_to_db(row['Name'], row['Description'], row['Answer'], row['Tags'].split(','), model['version'], False)

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
    st.write('Are you sure you want to delete the selected tasks?')

    confirm_col, cancel_col, _, _ = st.columns([1,1,2,2])
    if confirm_col.button('Yes', use_container_width=True):
        delete_tasks_from_list(task_ids)
        st.rerun()
    
    if cancel_col.button('No', use_container_width=True, type='primary'):
        st.rerun()


tasks_heading = '## Tasks'

num_tasks = len(st.session_state.tasks)

if num_tasks > 0:
    tasks_heading = f'## Tasks ({num_tasks})'

st.write(tasks_heading)

verify_col, save_col, _, _, _ = st.columns([2,3,1,1, 1])

is_verify_mode = verify_col.checkbox('Verify Mode', value=False, help='Select this to go through the unverified answers and verify them for learners to access them.')

if not st.session_state.tasks:
    st.error('No tasks added yet')
    st.stop()

df = pd.DataFrame(st.session_state.tasks)

column_config={
            'id': None
}

column_order = ['verified', 'name', 'description', 'answer', 'tags', 'generation_model', 'timestamp']


def save_changes_in_verify_mode(edited_df):
    # identify the rows that have been changed
    # and update the db with the new values
    # import ipdb; ipdb.set_trace()
    changed_rows = edited_df[(df != edited_df).any(axis=1)]
    
    for _, row in changed_rows.iterrows():
        task_id = row['id']
        # print(task_id)
        update_task_in_db(task_id, row['name'], row['description'], row['answer'], row['tags'], row['generation_model'], row['verified'])
    
    # Refresh the tasks in the session state
    st.session_state.tasks = get_all_tasks()
    st.toast('Changes saved successfully!')
    # st.rerun()

if not is_verify_mode:
    df_actions = st.container()

    event = st.dataframe(
        df,
        on_select='rerun',
        selection_mode='multi-row',
        hide_index=True,
        use_container_width=True,
        column_config=column_config,
        column_order=column_order
    )


    if len(event.selection['rows']):
        if df_actions.button('Delete selected tasks'):
            # import ipdb; ipdb.set_trace()
            show_delete_confirmation(df.iloc[event.selection['rows']]['id'].tolist())

else:
    edited_df = st.data_editor(df, hide_index=True, column_config=column_config, column_order=column_order, use_container_width=True)

    if not df.equals(edited_df):
        save_col.button('Save changes', type='primary', on_click=partial(save_changes_in_verify_mode, edited_df))
            


