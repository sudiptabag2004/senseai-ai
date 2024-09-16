import streamlit as st
import pandas as pd
import time
from lib.db import get_all_tasks, get_solved_tasks_for_user
from lib.init import init_env_vars, init_db

init_env_vars()
init_db()

if 'email' not in st.query_params:
    st.error('Not authorized. Redirecting to home page...')
    time.sleep(2)
    st.switch_page('./home.py')

st.session_state.email = st.query_params['email']

st.write('## Tasks')
st.write('Select a task by clicking beside the index of the task')

st.session_state.tasks = get_all_tasks()
solved_task_ids = get_solved_tasks_for_user(st.session_state.email)

df = pd.DataFrame(st.session_state.tasks)

df['status'] = df['id'].apply(lambda x: '✅' if x in solved_task_ids else '')

if not len(df):
    st.error('No tasks added yet. Ask you mentors/teachers to add tasks for you to solve.')
    st.stop()

filtered_df = df[df['verified']][['status', 'id', 'name', 'description', 'tags']]

if not len(filtered_df):
    st.error('No tasks added yet. Ask you mentors/teachers to add tasks for you to solve.')
    st.stop()


df_actions = st.container(border=True)

event = st.dataframe(
    filtered_df.style.map(
        lambda _: "background-color: green;", subset=(filtered_df[filtered_df['status'] != ''].index, slice(None))
    ),
    on_select='rerun',
    selection_mode='single-row',
    use_container_width=True,
    hide_index=True, 
    column_order=['status', 'id', 'tags', 'name', 'description'],
    column_config={
        'description': st.column_config.TextColumn(
            width='medium',
            help='Description of the task'
        ),
        # 'id': None
    }
)


if len(event.selection['rows']):
    df_actions.write('Do you want to work on this task?')
    task_id = filtered_df.iloc[event.selection['rows'][0]]['id']
    df_actions.link_button('Yes', f'/task?id={task_id}&email={st.session_state.email}')
    # print()
        # delete_tasks(event.selection['rows'])