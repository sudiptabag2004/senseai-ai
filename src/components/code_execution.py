import subprocess
import tempfile
import re
import streamlit as st


def run_nodejs_code(code: str) -> str:
    """Execute Node.js code and return the output."""
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as temp_file:
        temp_file.write(code.encode("utf-8"))
        temp_file_path = temp_file.name

    try:
        output = subprocess.check_output(
            ["node", temp_file_path], stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"

    return output


def run_python_code(code: str) -> str:
    """Execute Python code and return the output."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(code.encode("utf-8"))
        temp_file_path = temp_file.name

    try:
        output = subprocess.check_output(
            ["python3", temp_file_path], stderr=subprocess.STDOUT, text=True
        )
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"

    return output


def retain_python_code():
    st.session_state["python_code"] = st.session_state["python_code"]


def get_python_user_input_instances(code: str):
    """Get all the user input instances in a given python code."""
    # account for different ways in which input() can be called and the fact that the input might have a prompt
    # e.g. int(input()), input("Blah blah"), = input(), =input()
    pattern = r"(?:^|\s|=|\()\s*input\([^)]*\)"
    matches = re.finditer(pattern, code)
    return [(match.start() + match[0].find("input"), match.end()) for match in matches]


def execute_code(code: str, lang: str):
    """Run code based on language and display output."""
    if lang == "NodeJS" or lang == "Javascript":
        output = run_nodejs_code(code)
    elif lang == "Python":
        if user_input_instances := get_python_user_input_instances(code):

            # Create text input widgets for each user input instance
            with st.expander("User Inputs"):
                st.markdown("Hit `Enter` after adding the input")
                for i, _ in enumerate(user_input_instances):
                    st.text_input(
                        f"Input {i+1}",
                        key=f"input_{i}",
                        on_change=retain_python_code,
                    )

            # Replace input() calls with the collected user inputs
            offset = 0
            for i, (start, end) in enumerate(user_input_instances):
                replacement = f"'{st.session_state[f'input_{i}']}'"
                code = code[: start + offset] + replacement + code[end + offset :]
                offset += len(replacement) - (end - start)

            # print(code)

        output = run_python_code(code)
    else:
        output = "Unsupported language for execution."

    # Display the output
    st.write("### Output")
    st.code(output, language="python" if lang == "Python" else "javascript")
