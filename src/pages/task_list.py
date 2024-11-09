import streamlit as st

st.set_page_config(layout="wide")

from auth import redirect_if_not_logged_in

redirect_if_not_logged_in()

user_email = st.query_params["email"]
st.markdown(
    f'This page has been moved. Go back to <a href="./?email={user_email}">home</a>!',
    unsafe_allow_html=True,
)


# cols = st.columns(2)
# with cols[0]:
#     show_streak()

# st.write("## Tasks")
# st.write("Select a task by clicking beside the index of the task")

# st.session_state.tasks = get_all_tasks()
# solved_task_ids = get_solved_tasks_for_user(st.session_state.email)

# df = pd.DataFrame(st.session_state.tasks)

# if not len(df):
#     st.error(
#         "No tasks added yet. Ask you mentors/teachers to add tasks for you to solve."
#     )
#     st.stop()

# df["status"] = df["id"].apply(lambda x: "✅" if x in solved_task_ids else "")

# filtered_df = df[df["verified"]][["status", "id", "name", "description", "tags"]]

# if not len(filtered_df):
#     st.error(
#         "No tasks added yet. Ask you mentors/teachers to add tasks for you to solve."
#     )
#     st.stop()


# df_actions = st.container(border=True)

# event = st.dataframe(
#     filtered_df.style.map(
#         lambda _: "background-color: #62B670;",
#         subset=(filtered_df[filtered_df["status"] != ""].index, slice(None)),
#     ),
#     on_select="rerun",
#     selection_mode="single-row",
#     use_container_width=True,
#     hide_index=True,
#     column_order=["id", "status", "tags", "name", "description"],
#     column_config={
#         # 'description': st.column_config.TextColumn(
#         #     width='large',
#         #     help='Description of the task'
#         # ),
#         # 'id': None
#     },
# )


# if len(event.selection["rows"]):
#     df_actions.write("Do you want to work on this task?")
#     task_id = filtered_df.iloc[event.selection["rows"][0]]["id"]
#     df_actions.link_button("Yes", f"/task?id={task_id}&email={st.session_state.email}")
#     # print()
#     # delete_tasks(event.selection['rows'])
