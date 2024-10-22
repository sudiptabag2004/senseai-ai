import streamlit as st
import colorsys
from typing import Dict


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


def show_progress_report_for_milestone(
    milestone: Dict, completed_tasks: int, total_tasks: int
):
    # Calculate the progress percentage
    progress_percentage = (completed_tasks / total_tasks) * 100

    header_bg_color = milestone["color"]
    progress_bg_color = generate_progress_bar_background_color(header_bg_color)

    # Generate a unique class name based on the milestone name
    milestone_class = f"milestone-{milestone['id']}"

    # Custom CSS for styling
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
        padding: 16px 20px;
    }}
    .milestone-name {{
        font-size: 24px;
        margin: 0;
        display: flex;
        align-items: center;
    }}
    .milestone-name svg {{
        margin-left: 8px;
        opacity: 0.6;
    }}
    .completed-tasks {{
        color: #666;
        margin: 2px 0 0 0;
        font-size: 14px;
    }}
    .{milestone_class} .progress-section {{
        padding: 16px 20px;
        background-color: {progress_bg_color};
    }}
    .progress-container {{
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
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Milestone container
    st.markdown(
        f"""
    <div class="milestone-container {milestone_class}">
        <div class="milestone-header">
            <h2 class="milestone-name">{milestone['name']}</h2>
            <p class="completed-tasks">Completed: {completed_tasks} / {total_tasks}</p>
        </div>
        <div class="progress-section">
            <p class="progress-percentage">{progress_percentage:.0f}%</p>
            <div class="progress-container">
                <div class="progress-bar"></div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
