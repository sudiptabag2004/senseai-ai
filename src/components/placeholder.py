import os
import streamlit as st
from typing import Literal


def show_no_courses_placeholder(
    view: Literal["home", "cohort"] = "home",
):
    if view == "home":
        _, container, _ = st.columns([1, 2, 1])
    else:
        container, _, _ = st.columns([2, 1, 1])

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"
        primary_btn_bg = "#FF4B4B"
        primary_btn_hover = "#ff3333"
        secondary_btn_bg = "#338233" if is_dark else "#00CC66"
        secondary_btn_hover = "#00b359"

        admin_panel_url = f"{os.environ.get('APP_URL')}/admin?org_id={st.session_state["selected_org"]['id']}"

        if view == "home":
            title = "You don't have any courses yet!"
            description = "On SensAI, learning happens through tasks. Learners receive feedback and questions from AI to nudge them in the right direction. Tasks are organized into courses. Start by creating your first course today!"
            button_text = "✨ Create Your First Course"
        else:
            title = "No courses in this cohort!"
            description = "On SensAI, learning happens through tasks. Learners receive feedback and questions from AI to nudge them in the right direction. Tasks are organized into courses. Start by creating a course and adding it to this cohort!"
            button_text = "✨ Create Or Add A Course"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 3rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 500px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    📚
                </div>
                <h2 style='
                    font-size: 1.5rem;
                    color: {text_color};
                    font-weight: 600;
                    margin-bottom: 1rem;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    {title}
                </h2>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    {description}
                </p>
                <a href='{admin_panel_url}' 
                    style='
                        text-decoration: none;
                        color: #fff;
                        background-color: {primary_btn_bg};
                        padding: 0.75rem 1.5rem;
                        border-radius: 8px;
                        display: inline-block;
                        font-weight: 500;
                        font-family: "Source Sans Pro", sans-serif;
                        transition: all 0.2s ease;
                        box-shadow: 0 2px 4px rgba(255, 75, 75, 0.1);
                        width: 250px;
                    '
                    onmouseover="this.style.backgroundColor='{primary_btn_hover}'; this.style.transform='translateY(-1px)'"
                    onmouseout="this.style.backgroundColor='{primary_btn_bg}'; this.style.transform='translateY(0)'"
                    role="button"
                    aria-label="Create a new course"
                >
                    {button_text}
                </a>
                <a href='https://docs.sensai.hyperverge.org/quickstart/' 
                    style='
                        text-decoration: none;
                        color: #fff;
                        margin-top: 1rem;
                        background-color: {secondary_btn_bg};
                        padding: 0.75rem 1.5rem;
                        border-radius: 8px;
                        display: inline-block;
                        font-weight: 500;
                        font-family: "Source Sans Pro", sans-serif;
                        transition: all 0.2s ease;
                        box-shadow: 0 2px 4px rgba(0, 204, 102, 0.1);
                        width: 250px;
                    '
                    onmouseover="this.style.backgroundColor='{secondary_btn_hover}'; this.style.transform='translateY(-1px)'"
                    onmouseout="this.style.backgroundColor='{secondary_btn_bg}'; this.style.transform='translateY(0)'"
                    role="button"
                    aria-label="Watch tutorials"
                >
                    📺 Watch Tutorials
                </a>
                <div style='margin-top: 2rem;'>
                    <a href='https://bit.ly/sensai_community' 
                        style='
                            color: {text_muted};
                            text-decoration: none;
                            font-size: 0.9rem;
                            border-bottom: 1px dashed {text_muted};
                        '
                        aria-label="View getting started guide"
                    >
                        Need help getting started?
                    </a>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )


def show_empty_cohorts_placeholder(section: Literal["dashboard", "analytics"]):
    container, _, _ = st.columns([1, 1, 1])

    if section == "dashboard":
        description = (
            "Cohorts help you organize learners and assign courses all in one place!"
        )
    else:
        description = f"""Create a cohort from the <a href="/admin?org_id={st.session_state.org_id}&section=0" target="_self" style="text-decoration: none; color: #00CC66;">dashboard</a> and add members to it. You will see their usage metrics here!"""

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"
        primary_btn_bg = "#FF4B4B"
        primary_btn_hover = "#ff3333"
        secondary_btn_bg = "#338233" if is_dark else "#00CC66"
        secondary_btn_hover = "#00b359"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 1.5rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 600px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    👥
                </div>
                <!-- Heading -->
                <div style='
                    font-size: 1.25rem;
                    color: {text_color};
                    font-weight: 600;
                    margin: 0 auto 1rem auto;
                    font-family: "Source Sans Pro", sans-serif;
                    display: inline-block;
                '>
                    You don't have any cohorts!
                </div>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    {description}
                </p>    
            </div>
        """,
            unsafe_allow_html=True,
        )


def show_empty_courses_placeholder():
    container, _, _ = st.columns([1, 1, 1])

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"
        primary_btn_bg = "#FF4B4B"
        primary_btn_hover = "#ff3333"
        secondary_btn_bg = "#338233" if is_dark else "#00CC66"
        secondary_btn_hover = "#00b359"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 1.5rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 600px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    📚
                </div>
                <!-- Heading -->
                <div style='
                    font-size: 1.25rem;
                    color: {text_color};
                    font-weight: 600;
                    margin: 0 auto 1rem auto;
                    font-family: "Source Sans Pro", sans-serif;
                    display: inline-block;
                '>
                    You don't have any courses yet!
                </div>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    Courses consist of tasks grouped into milestones that can be assigned to cohorts
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )


def show_empty_tasks_placeholder(align: Literal["center", "left"] = "center"):
    if align == "center":
        _, container, _ = st.columns([1, 2, 1])
    else:
        container = st.container()

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 1.5rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 600px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    ✍️
                </div>
                <!-- Heading -->
                <div style='
                    font-size: 1.25rem;
                    color: {text_color};
                    font-weight: 600;
                    margin: 0 auto 1rem auto;
                    font-family: "Source Sans Pro", sans-serif;
                    display: inline-block;
                '>
                    No tasks created yet
                </div>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    Tasks are the building blocks of learning on SensAI - create reading materials or questions for assessment
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )


def show_empty_milestones_placeholder():
    container, _, _ = st.columns([1, 1, 1])

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"
        primary_btn_bg = "#FF4B4B"
        primary_btn_hover = "#ff3333"
        secondary_btn_bg = "#338233" if is_dark else "#00CC66"
        secondary_btn_hover = "#00b359"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 1.5rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 600px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    🎯
                </div>
                <!-- Heading -->
                <div style='
                    font-size: 1.25rem;
                    color: {text_color};
                    font-weight: 600;
                    margin: 0 auto 1rem auto;
                    font-family: "Source Sans Pro", sans-serif;
                    display: inline-block;
                '>
                    No milestones created yet
                </div>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    Milestones help you group tasks within your course to create a structured learning path
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )


def show_empty_tags_placeholder():
    container, _, _ = st.columns([1, 1, 1])

    with container:
        # Set theme-dependent colors
        is_dark = st.session_state.theme["base"] == "dark"

        bg_gradient_start = "#2d2d2d" if is_dark else "#f7f7f7"
        bg_gradient_end = "#1e1e1e" if is_dark else "#ffffff"
        text_color = "#ffffff" if is_dark else "#262730"
        text_muted = "#999999" if is_dark else "#666666"
        shadow_color = "rgba(0,0,0,0.3)" if is_dark else "rgba(0,0,0,0.05)"
        primary_btn_bg = "#FF4B4B"
        primary_btn_hover = "#ff3333"
        secondary_btn_bg = "#338233" if is_dark else "#00CC66"
        secondary_btn_hover = "#00b359"

        # Create a styled container with centered content
        st.markdown(
            f"""
            <div style='
                text-align: center; 
                padding: 1.5rem; 
                background: linear-gradient(to bottom, {bg_gradient_start}, {bg_gradient_end});
                border-radius: 16px;
                box-shadow: 0 4px 6px {shadow_color};
                max-width: 600px;
                margin: auto;
            '>
                <!-- Illustration -->
                <div style='font-size: 3.5rem; margin-bottom: 1.5rem;'>
                    🏷️
                </div>
                <!-- Heading -->
                <div style='
                    font-size: 1.25rem;
                    color: {text_color};
                    font-weight: 600;
                    margin: 0 auto 1rem auto;
                    font-family: "Source Sans Pro", sans-serif;
                    display: inline-block;
                '>
                    No tags created yet
                </div>
                <p style='
                    color: {text_muted};
                    margin-bottom: 2rem;
                    font-size: 1rem;
                    line-height: 1.5;
                    font-family: "Source Sans Pro", sans-serif;
                '>
                    Tags help you categorize tasks and make them easier to organize and find
                </p>
            </div>
        """,
            unsafe_allow_html=True,
        )
