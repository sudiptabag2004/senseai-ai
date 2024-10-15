import streamlit as st
from lib.db import get_streaks
from .base import set_box_style, show_box_header


def show_leaderboard():

    streaks = get_streaks()
    streaks = sorted(streaks.items(), key=lambda x: x[1], reverse=True)[:3]

    set_box_style()

    with st.container(border=True):
        # Header
        show_box_header("Top Performers")

        for i, (email, streak_count) in enumerate(streaks):
            col1, col2 = st.columns([1, 5])

            with col1:
                medal_image = open(f"lib/assets/leaderboard_{i+1}.svg").read()

                # Center the image vertically
                st.markdown(
                    f'<div style="display: flex; justify-content: center; align-items: center; height: 100%;">'
                    f"{medal_image}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f'<p style="text-decoration: none; margin-bottom: 0;">{email}</p>'
                    f'<p style="margin-top: 0;">Streak: {streak_count}</p>',
                    unsafe_allow_html=True,
                )

            if i < len(streaks) - 1:
                st.markdown(
                    '<div class="separator"></div>',
                    unsafe_allow_html=True,
                )
