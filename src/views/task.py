import streamlit as st
from views.roadmap import get_tasks_with_completion_status
from components.milestone_learner_view import get_task_url


def display_milestone_tasks_in_sidebar(user_id, course_id, cohort_id, task):
    course_tasks = get_tasks_with_completion_status(
        user_id, cohort_id, course_id, task["milestone_id"]
    )

    with st.sidebar.container(border=True):
        st.subheader(task["milestone_name"])

    for index, course_task in enumerate(course_tasks):
        course_text_to_display = course_task["name"].strip()

        if course_task["completed"]:
            course_text_to_display = "✅ " + course_text_to_display

        task_url = get_task_url(course_task, cohort_id, course_id)

        if course_task["id"] == task["id"]:
            current_task_index = index
            st.sidebar.markdown(
                f"""<div style='background-color: #ADADB2; padding: 8px 12px; border-radius: 0.5rem; margin: 0 0 16px 0;'>{course_text_to_display}</div>""",
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.markdown(
                f'<a href="{task_url}" target="_self" style="text-decoration: none; background-color: #dfe3eb; padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">{course_text_to_display}</a>',
                unsafe_allow_html=True,
            )

    prev_task = course_tasks[current_task_index - 1] if current_task_index > 0 else None
    next_task = (
        course_tasks[current_task_index + 1]
        if current_task_index < len(course_tasks) - 1
        else None
    )

    return prev_task, next_task


def show_task_name(task, bg_color, text_color, is_solved):
    DEFAULT_BACKGROUND_COLOR = "#1B83E1"
    DEFAULT_TEXT_COLOR = "#FFFFFF"

    kwargs = {
        "background_color": DEFAULT_BACKGROUND_COLOR,
        "text_color": DEFAULT_TEXT_COLOR,
    }

    if bg_color is not None:
        kwargs["background_color"] = bg_color
    if text_color is not None:
        kwargs["text_color"] = text_color

    st.markdown(
        f"""<div style='padding: 0.5rem 1rem; border-radius: 0.5rem; background-color: {kwargs["background_color"]}; color: {kwargs["text_color"]};'>{task['name'].strip()}</div>""",
        unsafe_allow_html=True,
    )
