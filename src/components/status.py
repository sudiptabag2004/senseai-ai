import streamlit as st


def error_markdown(text: str):
    text_color = "#FFDEDE" if st.session_state.theme["base"] == "dark" else "#7D353A"
    background_color = (
        "#3D2429" if st.session_state.theme["base"] == "dark" else "#F3E1E5"
    )

    st.markdown(
        f"""
    <div id="status_error_markdown" style="
        background-color: {background_color};
        color: {text_color};
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    ">
        <span style="color: {text_color}">
            {text}
        </span>
        <style>
            #status_error_markdown a {{
                color: #00CC66 !important;
                text-decoration: none;
            }}
        </style>
    </div>
    """,
        unsafe_allow_html=True,
    )
