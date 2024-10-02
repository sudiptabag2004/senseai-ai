import subprocess
import tempfile
import streamlit as st

def run_nodejs_code(code: str) -> str:
    """Execute Node.js code and return the output."""
    with tempfile.NamedTemporaryFile(suffix=".js", delete=False) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name

    try:
        output = subprocess.check_output(['node', temp_file_path], stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"

    return output

def run_python_code(code: str) -> str:
    """Execute Python code and return the output."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name

    try:
        output = subprocess.check_output(['python3', temp_file_path], stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as e:
        output = f"Error: {e.output}"

    return output

def execute_code(code: str, lang: str):
    """Run code based on language and display output."""
    if lang == 'NodeJS' or lang == 'Javascript':
        output = run_nodejs_code(code)
    elif lang == 'Python':
        output = run_python_code(code)
    else:
        output = "Unsupported language for execution."

    # Display the output
    st.write("### Output")
    st.code(output, language='python' if lang == 'Python' else 'javascript')