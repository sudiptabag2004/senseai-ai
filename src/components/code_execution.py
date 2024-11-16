from typing import List, Dict, Tuple
import subprocess
import tempfile
import re
import streamlit as st
import asyncio
import json
import streamlit.components.v1 as components


def show_react_help_text():
    with st.expander("Learn More"):
        working_code_sample = """function ToggleButton() {\n  const [isOn, setIsOn] = React.useState(false);\n\n  const toggle = () => {\n    setIsOn(prevState => !prevState);\n  };\n\n  return (\n    <button onClick={toggle}>\n      {isOn ? 'On' : 'Off'}\n    </button>\n  );\n}\n\nconst rootElement = document.getElementById('root');\nReactDOM.render(<ToggleButton />, rootElement);"""
        failing_code_sample = """import React, { useState } from 'react';\n\nfunction ToggleButton() {\n  const [isOn, setIsOn] = useState(false);\n\n  const toggle = () => {\n    setIsOn(prevState => !prevState);\n  };\n\n  return (\n    <button onClick={toggle}>\n      {isOn ? 'On' : 'Off'}\n    </button>\n  );\n}\n\nconst rootElement = document.getElementById('root');\nReactDOM.render(<ToggleButton />, rootElement);"""

        st.markdown(
            f"A few guidelines to follow:\n- Avoid importing `React` or `useState`. Directly use `React.useState` and so on.\n- Structure your code to adhere to the initial code template provided.\n- If your code does not produce the desired output, check if it follows these principles (refer to the example below).\n\nHere is a code sample that produces the desired output.\n\n```jsx\n{working_code_sample}\n```\nBut the following code does not:\n\n```jsx\n{failing_code_sample}\n```"
        )


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


async def run_python_code_with_timeout(code: str, timeout: int = 60):
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_file:
        temp_file.write(code.encode("utf-8"))
        temp_file_path = temp_file.name

    try:
        process = await asyncio.create_subprocess_exec(
            "python3",
            temp_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
            if stderr:
                return f"Error: {stderr.decode()}"
            return stdout.decode()
        except asyncio.TimeoutError:
            process.kill()
            return "Timeout: Code execution took too long"
    except Exception as e:
        return f"Error: {str(e)}"


def retain_python_code():
    st.session_state["python_code"] = st.session_state["python_code"]


def get_python_user_input_instances(code: str):
    """Get all the user input instances in a given python code."""
    # account for different ways in which input() can be called and the fact that the input might have a prompt
    # e.g. int(input()), input("Blah blah"), = input(), =input()
    pattern = r"(?:^|\s|=|\()\s*input\([^)]*\)"
    matches = re.finditer(pattern, code)
    return [(match.start() + match[0].find("input"), match.end()) for match in matches]


def replace_inputs_in_code(
    code: str, user_input_instances: List[Tuple[int, int]], inputs: List[str]
):
    offset = 0
    for i, (start, end) in enumerate(user_input_instances):
        replacement = f"{repr(inputs[i])}"
        code = code[: start + offset] + replacement + code[end + offset :]
        offset += len(replacement) - (end - start)

    return code


def replace_inputs_in_code_with_test_inputs(code: str, inputs: List[str]):
    user_input_instances = get_python_user_input_instances(code)
    if len(user_input_instances) != len(inputs):
        st.error(
            f"Number of inputs in code ({len(user_input_instances)}) does not match number of provided inputs ({len(inputs)})"
        )

    return replace_inputs_in_code(code, user_input_instances, inputs)


def run_react_code(jsx_code: str, css_code: str) -> str:
    """Generate HTML for executing React code."""
    react_template = f"""
    <style>
        {css_code}
    </style>
    <div id="root"></div>
    <script src="https://unpkg.com/react/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/babel-standalone/babel.min.js"></script>
    <script type="text/babel">
        {jsx_code}
    </script>
    """
    return react_template


def execute_code(code: str, lang: str, width: int = 600, height: int = 300):
    """Run code based on language and display output."""
    if lang == "NodeJS" or lang == "Javascript":
        output = run_nodejs_code(code)
    elif lang == "Python":
        user_input_instances = get_python_user_input_instances(code)
        user_input_keys = []

        if user_input_instances:
            # Create text input widgets for each user input instance
            with st.expander("User Inputs", expanded=True):
                st.markdown(
                    "Your code requires user inputs to run. Hit `Enter` after adding each input"
                )
                for i, _ in enumerate(user_input_instances):
                    user_input_key = f"input_{i}"
                    st.text_input(
                        f"Input {i+1}",
                        key=user_input_key,
                        on_change=retain_python_code,
                    )
                    user_input_keys.append(user_input_key)

            # Replace input() calls with the collected user inputs
            inputs = [st.session_state[key] for key in user_input_keys]
            code = replace_inputs_in_code(
                code,
                user_input_instances,
                inputs,
            )

            if any(input is None or input == "" for input in inputs):
                st.info(
                    "You have provided one or more empty inputs. Is your code supposed to run correctly with empty inputs?"
                )
                if not st.checkbox(
                    "Yes, my code works correctly for empty inputs",
                    on_change=retain_python_code,
                ):
                    return

            # print(code)

        output = asyncio.run(run_python_code_with_timeout(code))
    elif lang == "React":
        output = run_react_code(code, st.session_state.css_code)
    else:
        output = "Unsupported language for execution."

    # Display the output
    st.write("### Output")
    if lang == "React":
        components.html(output, width=width, height=height, scrolling=True)
    else:
        st.code(output, language="python" if lang == "Python" else "javascript")


def run_tests(code: str, tests: List[Dict]):
    results = []
    for test in tests:
        try:
            test_code = replace_inputs_in_code_with_test_inputs(code, test["input"])
            output = asyncio.run(run_python_code_with_timeout(test_code))

            if output.strip() == "Timeout: Code execution took too long":
                results.append({"status": "timeout", "output": output})
            elif output.strip() == test["output"].strip():
                results.append({"status": "passed", "output": output})
            else:
                results.append({"status": "failed", "output": output})
        except ValueError as e:
            raise e
        except Exception as e:
            results.append({"status": "error", "output": str(e)})

    return results


react_default_code = """
function App() {


  return (
    <></>
  );
}

const rootElement = document.getElementById('root');
ReactDOM.render(<App />, rootElement);
"""
