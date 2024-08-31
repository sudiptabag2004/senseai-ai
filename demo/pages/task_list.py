import streamlit as st
import pandas as pd
from lib.utils import load_json

st.write('## Tasks')
st.write('Select a task by clicking beside the index of the task')

tasks_local_path = './db/tasks.json'

st.session_state.tasks = load_json(tasks_local_path)

if not st.session_state.tasks:
    st.error('No tasks added yet')
    st.stop()

df = pd.DataFrame(st.session_state.tasks)

df_actions = st.container(border=True)

filtered_df = df[df['verified']][['name', 'description', 'tags']]


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
        '_index': st.column_config.TextColumn(
            label='Task Index'
        )
    }
)


if len(event.selection['rows']):
    df_actions.write('Do you want to start this task?')
    task_index = filtered_df.index[event.selection['rows'][0]]
    df_actions.link_button('Yes', '/task?index=' + str(task_index))
    # print()
        # delete_tasks(event.selection['rows'])