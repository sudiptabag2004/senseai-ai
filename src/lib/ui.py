import streamlit as st
import html
import re


def display_waiting_indicator():
    st.markdown(
        """
        <style>
        .typing-indicator {
            display: flex;
            align-items: center;
            height: 20px;
        }
        .typing-indicator span {
            display: inline-block;
            width: 5px;
            height: 5px;
            margin: 0 2px;
            background: #999;
            border-radius: 50%;
            animation: bounce 1s infinite alternate;
        }
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes bounce {
            from { transform: translateY(0); }
            to { transform: translateY(-15px); }
        }
        </style>
        <div class="typing-indicator">
            <span></span><span></span><span></span>
        </div>
    """,
        unsafe_allow_html=True,
    )


def show_singular_or_plural(count: int, label: str):
    return f"{count} {label}" if count == 1 else f"{count} {label}s"


def correct_code_blocks(text: str):
    """
    If the code blocks are not properly closed, fix it.
    This means that the ending ``` should be on a new line
    and anything after that should be in a new line
    """
    # Split text into sections based on code blocks
    sections = []
    last_end = 0

    # Find all code blocks
    for match in re.finditer(r"```.*?\n.*?```", text, re.DOTALL):
        # Add text before code block unchanged
        if match.start() > last_end:
            sections.append(text[last_end : match.start()])

        # Get the code block content
        code_block = text[match.start() : match.end()]

        # Fix the code block ending if needed
        if not code_block.endswith("\n```\n"):
            # Remove any trailing ```
            code_block = code_block.rstrip()
            if code_block.endswith("```"):
                code_block = code_block[:-3]
            # Ensure proper ending format
            code_block = code_block.rstrip() + "\n```\n"

        sections.append(code_block)
        last_end = match.end()

    # Add any remaining text after last code block
    if last_end < len(text):
        sections.append(text[last_end:])

    return "".join(sections)


def escape_text_outside_code_blocks(text: str):
    """
    Split content into sections based on code blocks based on ```
    and escape the text before and after the code blocks; since
    streamlit correctly renders code within ```, don't escape it
    """
    sections = []
    last_end = 0

    # Find all code blocks
    for match in re.finditer(r"```.*?\n.*?```", text, re.DOTALL):
        # Add escaped text before code block
        if match.start() > last_end:
            sections.append(html.escape(text[last_end : match.start()]))
        # Add unescaped code block
        sections.append(text[match.start() : match.end()])
        last_end = match.end()

    # Add any remaining text after last code block
    if last_end < len(text):
        sections.append(html.escape(text[last_end:]))

    return "".join(sections)


def correct_newlines_outside_code_blocks(text: str):
    """
    Streamlit renders newlines within ``` as actual newlines, so we need to
    correct that by replacing \n with \n\n. Only do this for text outside
    code blocks.
    """
    sections = []
    last_end = 0

    # Find all code blocks
    for match in re.finditer(r"```.*?\n.*?```", text, re.DOTALL):
        # Add text before code block with newlines replaced
        if match.start() > last_end:
            non_code_text = text[last_end : match.start()]
            non_code_text = non_code_text.replace("\n", "\n\n")
            sections.append(non_code_text)
        # Add unescaped code block
        sections.append(text[match.start() : match.end()])
        last_end = match.end()

    # Add any remaining text after last code block with newlines replaced
    if last_end < len(text):
        non_code_text = text[last_end:]
        non_code_text = non_code_text.replace("\n", "\n\n")
        sections.append(non_code_text)

    return "".join(sections)
