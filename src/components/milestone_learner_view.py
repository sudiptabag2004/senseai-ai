import streamlit as st
import colorsys
import html
from typing import Dict, List


def generate_progress_bar_background_color(header_background_color: str):
    # Convert header color from hex to RGB
    header_rgb = tuple(
        int(header_background_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
    )

    # Convert RGB to HSV
    h, s, v = colorsys.rgb_to_hsv(
        header_rgb[0] / 255, header_rgb[1] / 255, header_rgb[2] / 255
    )

    # Create a lighter color for the progress section
    progress_rgb = colorsys.hsv_to_rgb(h, s * 0.5, min(1, v * 1.2))

    # Convert RGB values to hex
    progress_color = "#{:02x}{:02x}{:02x}".format(
        int(progress_rgb[0] * 255),
        int(progress_rgb[1] * 255),
        int(progress_rgb[2] * 255),
    )

    return progress_color


def get_task_view_style():
    if "theme" not in st.session_state:
        st.session_state.theme = {"base": "light"}

    container_color = "#fff"
    if st.session_state.theme["base"] == "dark":
        container_color = "#0E1117"

    task_view_style = f""".task-list-container {{
        background-color: {container_color};
        padding: 8px 16px;
        max-height: calc(2 * (20px + 1.4em * 3 + 8px + 32px + 20px)); /* Approximate height of 2 tasks */
        overflow-y: auto;
        margin-bottom: 20px;
    }}
    
    .task-item {{
        display: flex;
        align-items: flex-start;
        padding-bottom: 20px;
        margin-bottom: 20px;
    }}
    .task-item:last-child {{
        margin-bottom: 0;
        padding-bottom: 0;
    }}

    .task-item:not(:last-child) {{
        border-bottom: 1px solid #e0e0e0;
    }}
    
    .task-checkbox {{
        flex-shrink: 0;
        margin-top: 15px;
        margin-right: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
    }}
    .task-checkbox svg {{
        width: 100%;
        height: 100%;
    }}
    .task-content {{
        flex-grow: 1;
        min-width: 0; /* Allows content to shrink below its minimum content size */
    }}
    .task-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
    }}
    .task-name {{
        font-size: 16px;
        font-weight: 500;
        margin-bottom: 0;  /* Remove bottom margin since it's now in a flex container */
        flex: 1;          /* Allow task name to take available space */
        margin-right: 16px; /* Add some space between name and button */
    }}
    .open-task-btn {{
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 6px 12px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 14px;
        margin-top: 8px;
        cursor: pointer;
        border-radius: 4px;
    }}
    a:link {{
        color: white;
        text-decoration: none;
    }}
    a:visited {{
        color: white;
        text-decoration: none;
    }}
    a:hover {{
        color: white;
        text-decoration: none;
    }}
    a:active {{
        color: white;
        text-decoration: none;
    }}"""
    return task_view_style


def set_task_view_style():
    st.markdown(f"""<style>{get_task_view_style()}</style>""", unsafe_allow_html=True)


def get_task_url(task: Dict, cohort_id: int, course_id: int):
    return f"/task?id={task['id']}&cohort={cohort_id}&course={course_id}"


def get_task_view(task: Dict, cohort_id: int, course_id: int, show_button: bool = True):
    if "theme" not in st.session_state or not st.session_state.theme:
        st.session_state.theme = {"base": "light"}

    task_url = get_task_url(task, cohort_id, course_id)

    incomplete_task_icon_name = "border_circle.svg"
    if st.session_state.theme["base"] == "dark":
        incomplete_task_icon_name = "border_circle_white.svg"

    progress_icon_name = (
        "green_tick.svg" if task["completed"] else incomplete_task_icon_name
    )
    progress_icon = open(f"lib/assets/{progress_icon_name}").read()

    # Escape HTML characters in task name and description
    task_name = html.escape(task["name"].strip())
    if len(task_name) > 50:
        task_name = task_name[:50] + "..."

    button_text = "Open Task"
    if task["type"] == "reading_material":
        button_text = "Read"

    open_task_button_html = f"""\t\t\t<a href="{task_url}" class="open-task-btn" style="visibility: {'' if show_button else 'hidden'}">{button_text}</a>\n"""
    return f"""<div class="task-item">\n\t<div class="task-checkbox">{progress_icon}</div>\n\t<div class="task-content">\n\t\t<div class="task-header">\n\t\t\t<div class="task-name">{task_name}</div>\n{open_task_button_html}\t\t</div>\n\t</div>\n</div>"""


def get_milestone_card_text_colors(header_bg_color: str):
    # Convert hex to RGB for luminance calculation
    hex_color = header_bg_color.lstrip("#")
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    # Calculate relative luminance using sRGB formula
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Use white text for dark backgrounds (luminance < 0.5)
    text_color = "#ffffff" if luminance < 0.5 else "#000000"
    num_completed_tasks_color = "#ebf0f0" if luminance < 0.5 else "#1b1c1c"

    return text_color, num_completed_tasks_color


def show_milestone_card(
    milestone: Dict,
    completed_tasks: int,
    total_tasks: int,
    tasks: List[Dict],
    cohort_id: int,
    course_id: int,
):
    # Calculate the progress percentage
    progress_percentage = (completed_tasks / total_tasks) * 100

    header_bg_color = milestone["color"]
    progress_bg_color = generate_progress_bar_background_color(header_bg_color)

    milestone_name_color, num_completed_tasks_color = get_milestone_card_text_colors(
        header_bg_color
    )

    # Generate a unique class name based on the milestone name
    milestone_class = f"milestone-{milestone['id']}"

    task_list_view = "".join(
        get_task_view(task, cohort_id, course_id) for task in tasks
    )

    st.markdown(
        f"""
    <style>
    .milestone-container {{
        background-color: #fff;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        overflow: hidden;
    }}
    .{milestone_class} .milestone-header {{
        background-color: {header_bg_color};
        padding: 0px 20px 8px 20px;
    }}
    .{milestone_class} .milestone-name {{
        font-size: 16px;
        margin: 0;
        display: flex;
        align-items: center;
        color: {milestone_name_color};
    }}
    .milestone-name svg {{
        margin-left: 8px;
        opacity: 0.6;
    }}
    .{milestone_class} .completed-tasks {{
        color: {num_completed_tasks_color};
        margin: -16px 0 0 0;
        font-size: 12px;
    }}
    .{milestone_class} .progress-section {{
        padding: 4px 20px 4px 20px;
        background-color: {progress_bg_color};
    }}
    .{milestone_class} .progress-container {{
        background-color: #E0E0E0;
        border-radius: 100px;
        height: 8px;
        margin-bottom: 8px;
    }}
    .{milestone_class} .progress-bar {{
        background-color: #4CAF50;
        height: 100%;
        border-radius: 100px;
        width: {progress_percentage}%;
    }}
    .progress-percentage {{
        text-align: right;
        font-size: 14px;
        margin-bottom: 4px;
        color: #000;
    }}
    {get_task_view_style()}
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""<div class="milestone-container {milestone_class}">\n\t<div class="milestone-header">\n\t\t<div class="milestone-left">\n\t\t\t<h2 class="milestone-name">{milestone['name']}</h2>\n\t\t\t<p class="completed-tasks">Completed: {completed_tasks} / {total_tasks}</p>\n\t\t</div>\n\t</div>\n\t<div class="progress-section">\n\t\t<p class="progress-percentage">{progress_percentage:.0f}%</p>\n\t\t<div class="progress-container">\n\t\t\t<div class="progress-bar"></div>\n\t\t</div>\n\t</div>\n</div>""",
        unsafe_allow_html=True,
    )

    with st.expander("Show tasks"):
        st.markdown(
            f"""<div class="task-list-container">\n\t\t{task_list_view}\n\t</div>""",
            unsafe_allow_html=True,
        )
