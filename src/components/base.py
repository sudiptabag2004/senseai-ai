import streamlit as st


def set_box_style():
    st.markdown(
        """
    <style>
    .container {
        background-color: #FEECBF;
        padding: 10px;
        border-radius: 2px;
        border: 1px solid #E0E0E0;
        margin-top: -16px;
        margin-left: -16px;
        margin-right: -16px;
        margin-bottom: 16px;
    }
    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 10px 0 0 10px;
        font-size: 32px;
        font-weight: bold;
    }
    .separator {
        height: 1px;
        background-color: #E0E0E0;
        margin: 0 0 20px 0;
        margin-left: -16px;
        margin-right: -16px;
    }
    .stMarkdown {
        margin-bottom: 0 !important;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def show_box_header(header_text: str):

    st.markdown(
        f"""
        <div class="container">
            <div class="header">
                <h5>{header_text}</h5>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
