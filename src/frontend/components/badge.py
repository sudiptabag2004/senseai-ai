import io
from os.path import join
import random
from typing import Dict, List
from pathlib import Path
import os
import requests
import json
import streamlit as st
from streamlit_extras.let_it_rain import rain

from lib.image import (
    get_image_embed_for_html,
    convert_html_to_image,
    standardize_image_size,
)
from lib.badge import (
    get_badge_by_id,
    get_cohort_badge_by_type_and_user_id,
    delete_badge_by_id,
    update_badge,
    create_badge,
)
from lib.emoji import generate_emoji
from lib.utils import get_current_time_in_ist

root_dir = "./lib"


TEMPLATES = {
    "longest_streak": {
        "learner": {
            "end_description": "You set a new record for your longest streak!",
        },
        "share": {
            "end_description": "I set a new record for my longest streak!",
        },
    },
    "streak": {
        "learner": {
            "end_description": "day streak!",
        },
        "share": {
            "start_description": "I am on a",
            "end_description": "day learning streak!",
        },
    },
    "milestone": {
        "learner": {
            "start_description": "You have mastered",
        },
        "share": {
            "start_description": "I have mastered",
        },
    },
}


def get_badge_params(image_path: str = None):
    # Generate random background color
    bg_color = f"rgb({random.randint(240, 255)}, {random.randint(240, 255)}, {random.randint(240, 255)})"

    # Get random badge image path
    if not image_path:
        badge_dir = Path(root_dir + "/assets/badges")
        badge_images = list(badge_dir.glob("*.png"))
        badge_name = random.choice(badge_images).name
        image_path = join(badge_dir, badge_name)

    return {
        "bg_color": bg_color,
        "image_path": image_path,
    }


BADGE_TYPE_TO_IMAGE_PATH = {
    "streak": root_dir + "/assets/streak_current.png",
    "longest_streak": root_dir + "/assets/streak_longest.png",
}


def create_new_badge_with_updates_to_existing_badges(
    user_id: int,
    emphasis_value: str,
    badge_type: str,
    cohort_id: int,
) -> int:
    image_path = None

    if badge_type == "streak":

        image_path = BADGE_TYPE_TO_IMAGE_PATH[badge_type]

        existing_streak_badge = get_cohort_badge_by_type_and_user_id(
            user_id, badge_type, cohort_id
        )

        if existing_streak_badge:
            # no new streak badge to create
            if existing_streak_badge["value"] == emphasis_value:
                return None

            if int(existing_streak_badge["value"]) > int(emphasis_value):
                # if a bigger streak existed before and a new streak has restarted,
                # convert the previous streak badge to a longest_streak badge if no
                # longest_streak badge exists; however, do nothing if a longest_streak
                # badge already exists as it would automatically be updated as the
                # current streak surpasses longest_streak elsewhere in the code
                longest_streak_badge = get_cohort_badge_by_type_and_user_id(
                    user_id, "longest_streak", cohort_id
                )
                if not longest_streak_badge:
                    update_badge(
                        existing_streak_badge["id"],
                        existing_streak_badge["value"],
                        "longest_streak",
                        BADGE_TYPE_TO_IMAGE_PATH["longest_streak"],
                        existing_streak_badge["bg_color"],
                    )
            else:
                # remove existing streak badge before replacing with new one
                delete_badge_by_id(existing_streak_badge["id"])

    elif badge_type == "longest_streak":
        image_path = BADGE_TYPE_TO_IMAGE_PATH[badge_type]
        existing_streak_badge = get_cohort_badge_by_type_and_user_id(
            user_id, badge_type, cohort_id
        )
        if existing_streak_badge:
            delete_badge_by_id(existing_streak_badge["id"])

    badge_params = get_badge_params(image_path)

    created_badge_id = create_badge(
        {
            "user_id": user_id,
            "value": emphasis_value,
            "badge_type": badge_type,
            "image_path": badge_params["image_path"],
            "bg_color": badge_params["bg_color"],
            "cohort_id": cohort_id,
        }
    )

    return created_badge_id


def get_badge_html(
    emphasis_value: str,
    badge_type: str,
    badge_view: str,
    badge_params: Dict,
    cohort_name: str,
    org_name: str,
    width: int = 300,
    height: int = 300,
):
    # hva_logo_embed_code = get_image_embed_for_html(
    #     root_dir + "/assets/hva_logo.jpeg", custom_class="logo", width=100
    # )
    logo_embed_code = get_image_embed_for_html(
        root_dir + "/assets/logo.png", custom_class="logo sensai-logo", width=100
    )
    badge_embed_code = get_image_embed_for_html(
        badge_params["image_path"],
        custom_class="badge-icon",
        width=400,
    )

    start_description = TEMPLATES[badge_type][badge_view].get("start_description", "")
    end_description = TEMPLATES[badge_type][badge_view].get("end_description", "")

    html_content = f"""
    <div class="badge" style="background-color: {badge_params['bg_color']};">
        
        
        <div class="badge-container">
           <div class="logo org-logo" style="width: 100px;">
                <p style="margin: 0;">{cohort_name}</p>
                <p style="margin: 0;">@{org_name}</p>
            </div>
            {logo_embed_code}
        </div>

        <div class="content">
            {badge_embed_code}
            <div class="text-overlay">
                {f'<p class="description start-description">{start_description}</p>' if start_description else ''}
                <p class="emphasis">{emphasis_value}</p>
                {f'<p class="description end-description">{end_description}</p>' if end_description else ''}
            </div>
        </div>
    </div>
    """

    x_multiplier = width / 300
    y_multiplier = height / 300

    css_content = f"""
    <style>
        .badge {{
            width: {width}px;
            height: {height}px;
            border-radius: 15px;
            padding: 20px;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            font-family: 'Comic Sans MS', 'Chalkboard SE', 'Marker Felt', sans-serif;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .badge-container {{
            position: relative;
            width: 100%;
            height: 20%;
        }}
        .logo {{
            position: absolute;
            max-width: 120px;  /* Adjust size as needed */
            height: auto;
        }}
        .logo.org-logo {{
            left: 0px;
            top: 10px;
            font-size: 12px;
        }}
        .logo.sensai-logo {{
            right: 0px;
            top: 10px;
        }}
        .content {{
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .badge-icon {{
            width: {150 * x_multiplier}px;
            height: auto;
            margin-bottom: {5 * y_multiplier}px;
        }}
        .text-overlay {{
            position: relative;
            z-index: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .emphasis {{
            font-size: {48 * x_multiplier}px;
            margin: 0;
            font-weight: bold;
            word-wrap: break-word;
            line-height: 1;
        }}
        .description {{
            font-size: {16 * x_multiplier}px;
            margin: {5 * y_multiplier}px 0;
            word-wrap: break-word;
        }}
        .start-description {{
            order: -1;
        }}
        .end-description {{
            order: 1;
        }}
    </style>
    """

    return css_content + html_content


def show_badge(
    emphasis_value: str,
    badge_type: str,
    badge_view: str,
    badge_params: Dict,
    cohort_name: str,
    org_name: str,
    width: int = 350,
    height: int = 350,
):
    badge_html = get_badge_html(
        emphasis_value,
        badge_type,
        badge_view,
        badge_params,
        cohort_name,
        org_name,
        width * 0.85,
        height * 0.85,
    )
    st.components.v1.html(badge_html, height=height, width=width)


@st.cache_data(show_spinner=False)
def generate_badge_image(
    emphasis_value: str,
    badge_type: str,
    badge_view: str,
    badge_params: Dict,
    cohort_name: str,
    org_name: str,
):
    badge_html = get_badge_html(
        emphasis_value, badge_type, badge_view, badge_params, cohort_name, org_name
    )
    return convert_html_to_image(badge_html)


def show_share_badge_prompt():
    st.markdown(
        """
        <style>
        .logo {
            width: 20px;
            height: auto;
            margin-bottom: 5px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    whatsapp_share_img = get_image_embed_for_html(
        root_dir + "/assets/logos/whatsapp.svg",
        custom_class="logo",
    )
    linkedin_share_img = get_image_embed_for_html(
        root_dir + "/assets/logos/linkedin.svg",
        custom_class="logo",
    )
    slack_share_img = get_image_embed_for_html(
        root_dir + "/assets/logos/slack.svg",
        custom_class="logo",
    )

    st.markdown(
        f"Share your achievement with others on {whatsapp_share_img} {linkedin_share_img} and {slack_share_img}!",
        unsafe_allow_html=True,
    )


def show_download_badge_button(
    emphasis_value: str,
    badge_type: str,
    badge_params: Dict,
    cohort_name: str,
    org_name: str,
    key: str = None,
):
    # Convert the image to bytes
    buffered = io.BytesIO()

    with st.spinner("Preparing for download..."):
        badge_share_image = generate_badge_image(
            emphasis_value, badge_type, "share", badge_params, cohort_name, org_name
        )

    badge_share_image.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()

    # Create a download button
    st.download_button(
        label="Download Badge",
        data=img_bytes,
        file_name=f"{badge_type}.png",
        mime="image/png",
        use_container_width=True,
        type="primary",
        key=f"download_badge_{key}",
    )


def _rain_emoji():
    emoji_to_rain = generate_emoji()
    rain(
        emoji=emoji_to_rain,
        font_size=32,
        falling_speed=15,
        animation_length="infinite",
    )


def _show_badge_in_dialog_box(badge_details: Dict, key: str = None):
    badge_params = {
        "image_path": badge_details["image_path"],
        "bg_color": badge_details["bg_color"],
    }

    with st.container():
        _, col2, _ = st.columns([0.25, 2, 0.5])

        with col2:
            show_badge(
                badge_details["value"],
                badge_details["type"],
                "learner",
                badge_params,
                badge_details["cohort_name"],
                badge_details["org_name"],
            )

        show_share_badge_prompt()

        show_download_badge_button(
            badge_details["value"],
            badge_details["type"],
            badge_params,
            badge_details["cohort_name"],
            badge_details["org_name"],
            key=key,
        )


@st.dialog(f"You unlocked a new badge! {generate_emoji()}")
def show_badge_dialog(badge_id: int):
    # _rain_emoji()
    badge_details = get_badge_by_id(badge_id)
    _show_badge_in_dialog_box(badge_details)


def get_badge_type_to_tab_details(badge_type: str) -> Dict:
    badge_type_to_tab_details = {
        "streak": {
            "title": "Current Streak",
            "help_text": "The streak that you are currently on!",
        },
        "longest_streak": {
            "title": "Longest Streak",
            "help_text": "The longest streak you have ever had!",
        },
    }
    return badge_type_to_tab_details.get(badge_type)


@st.dialog(f"You unlocked new badges! {generate_emoji()}")
def show_multiple_badges_dialog(badge_ids: List[int]):
    _rain_emoji()

    # st.markdown("You can view all your badges any time in your profile")

    all_badge_details = [get_badge_by_id(badge_id) for badge_id in badge_ids]
    all_tab_details = [
        get_badge_type_to_tab_details(badge_details["type"])
        for badge_details in all_badge_details
    ]
    tab_names = [tab_details["title"] for tab_details in all_tab_details]

    st.markdown(
        """
        <style>
        .stTabs {
            margin-top: -4rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs(tab_names)
    for index, tab in enumerate(tabs):
        with tab:
            st.markdown(all_tab_details[index]["help_text"])
            _show_badge_in_dialog_box(all_badge_details[index], key=f"{index}")


def standardize_badge_image(image_path: str):
    standardize_image_size(image_path, image_path, 600, 600)


def check_for_badges_unlocked(user_id: int, user_streak: List, cohort_id: int):
    # scenarios:
    # 1. streak does not exist - nothing to check in this case
    # 2. streak exists and now 1 more day is added to it
    #   a) if the check below does not pass: it means the streak for current day is already accounted for
    #   b) if the check below passes:
    #       i) it makes the current streak equal to the existing current streak badge value (e.g. if user deleted all messages for today and added new messages, then the streak will remain the same). Nothing to do in this case.
    #       ii) it makes the current streak greater than the existing current streak badge value. In this case, we need to update the current streak badge
    #           1. this current streak is the only streak the user ever had, nothing to do in this case
    #           2. this current streak is a new streak with a previously larger streak in history:
    #               a) if there is no longest streak badge, then, create a new longest streak badge with the older streak value
    #               b) if there is a longest streak badge, then, compare the current streak with the longest streak badge value and update the longest streak badge if the current streak is greater than the longest streak badge value and show it as a badge
    if not user_streak:
        return

    # if a streak already exists (of one or more days of continuous usage)
    today = get_current_time_in_ist().date()
    streak_last_date = user_streak[0]

    if (today - streak_last_date).days != 1:
        return

    current_streak = len(user_streak) + 1

    streak_badge_id = create_new_badge_with_updates_to_existing_badges(
        user_id,
        str(current_streak),
        "streak",
        cohort_id,
    )

    if streak_badge_id is None:
        return

    badges_to_show = [streak_badge_id]

    longest_streak_badge = get_cohort_badge_by_type_and_user_id(
        st.session_state.user["id"],
        "longest_streak",
        cohort_id,
    )

    # if no longest streak badge exists, then, the current streak is the first and longest streak
    # no need to do anything in this case
    # but if the longest streak badge exists, then, we need to compare the current streak with the longest streak
    # if the current streak is greater than the longest streak, then, we need to update the longest streak badge
    if longest_streak_badge is not None and current_streak > int(
        longest_streak_badge["value"]
    ):

        longest_streak_badge_id = create_new_badge_with_updates_to_existing_badges(
            user_id, str(current_streak), "longest_streak", cohort_id
        )
        badges_to_show.append(longest_streak_badge_id)

    return badges_to_show


def test_badge_image():
    badge_params = get_badge_params()
    image = generate_badge_image(
        "HTML",
        "streak",
        "learner",
        badge_params,
        "HVA 2024",
        "HyperVerge Academy",
    )
    image.save("test.png")


def test_badge_html():
    badge_params = get_badge_params()
    html = get_badge_html(
        "HTML",
        "streak",
        "learner",
        badge_params,
        "HVA 2024",
        "HyperVerge Academy",
    )
    with open("test.html", "w") as f:
        f.write(html)

    im = convert_html_to_image(html)
    im.save("test.png")


if __name__ == "__main__":
    root_dir = "../lib"
