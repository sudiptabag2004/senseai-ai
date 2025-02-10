import os
from typing import Dict, Literal
import streamlit as st


def back_to_home_button(params: Dict[str, str] = None, text: str = "🏠 Back to Home"):
    home_page_url = os.environ.get("APP_URL")

    if params:
        query_params = "&".join([f"{key}={value}" for key, value in params.items()])
        home_page_url += f"?{query_params}"

    st.markdown(
        f'<a href="{home_page_url}" target="_self" style="color: white; text-decoration: none; background-color: rgba(49, 51, 63, 0.4); padding: 0.5rem 1rem; border-radius: 0.5rem; display: inline-block;">{text}</a>',
        unsafe_allow_html=True,
    )


def link_button(
    text: str,
    url: str,
    icon: str = None,
    icon_position: Literal["left", "right"] = "left",
):
    icon_html = (
        f'<span style="margin-{"right" if icon_position == "left" else "left"}: 0.5rem; background-color: #787777; padding: 0.5rem 1rem;">{icon}</span>'
        if icon
        else ""
    )
    icon_content = (
        f"{icon_html}<span style='flex-grow: 1; margin-left: 0.5rem;'>{text}</span>"
        if icon_position == "left"
        else f"<span style='flex-grow: 1; margin-left: 1rem;'>{text}</span>{icon_html}"
    )

    st.markdown(
        f"""<a href="{url}" target="_self" style="color: white; text-decoration: none; background-color: rgba(49, 51, 63, 0.4); border-radius: 0.5rem; display: inline-block; width: 100%; text-align: left;">
            <div style="display: flex; align-items: center;">
                {icon_content}
            </div>
        </a>""",
        unsafe_allow_html=True,
    )
