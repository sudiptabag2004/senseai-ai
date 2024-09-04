import streamlit as st
import pandas as pd
from lib.db import get_all_tasks
from lib.init import init_db

init_db()

st.write('## Tasks')
st.write('Select a task by clicking beside the index of the task')

st.session_state.tasks = get_all_tasks()

if not st.session_state.tasks:
    st.error('No tasks added yet. Ask you mentors/teachers to add tasks for you to solve.')
    st.stop()

df = pd.DataFrame(st.session_state.tasks)

df_actions = st.container(border=True)

filtered_df = df[df['verified']][['id', 'name', 'description', 'tags']]


event = st.dataframe(
    filtered_df,
    on_select='rerun',
    selection_mode='single-row',
    use_container_width=True,
    # hide_index=True, 
    column_order=['_index', 'tags', 'name', 'description'],
    column_config={
        'description': st.column_config.TextColumn(
            width='medium',
            help='Description of the task'
        ),
        'id': None
    }
)


if len(event.selection['rows']):
    df_actions.write('Do you want to start this task?')
    task_id = filtered_df.iloc[event.selection['rows'][0]]['id']
    df_actions.link_button('Yes', '/task?id=' + str(task_id))
    # print()
        # delete_tasks(event.selection['rows'])