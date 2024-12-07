import streamlit as st
from views.roadmap import get_tasks_with_completion_status
from components.milestone_learner_view import get_task_url
from components.sticky_container import sticky_container


def display_milestone_tasks_in_sidebar(user_id, course_id, cohort_id, task):
    course_tasks = get_tasks_with_completion_status(
        user_id, cohort_id, course_id, task["milestone_id"]
    )

    with st.sidebar.container(border=True):
        st.subheader(task["milestone_name"])

    for course_task in course_tasks:
        course_text_to_display = course_task["name"].strip()

        if course_task["completed"]:
            course_text_to_display = "✅ " + course_text_to_display

        task_url = get_task_url(course_task, cohort_id, course_id)

        if course_task["id"] == task["id"]:
            st.sidebar.markdown(
                f"""<div style='background-color: #ADADB2; padding: 8px 12px; border-radius: 0.5rem; margin: 0 0 16px 0;'>{course_text_to_display}</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                f'<a href="{task_url}" target="_self" style="text-decoration: none; background-color: #dfe3eb; padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">{course_text_to_display}</a>',
                unsafe_allow_html=True,
            )


def show_task_name(task, bg_color, text_color, is_solved):
    with sticky_container(
        border=True,
        background_color=bg_color,
        text_color=text_color,
    ):
        # st.link_button('Open task list', '/task_list')

        heading = f"**{task['name'].strip()}**"
        if is_solved:
            heading += " ✅"
        st.write(heading)
