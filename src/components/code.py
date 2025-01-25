from typing import List, Dict, Tuple
import subprocess
import tempfile
import re
import streamlit as st
import asyncio
import json
import streamlit.components.v1 as components
import sqlite3
import pandas as pd
from streamlit_ace import st_ace, THEMES
from lib.config import coding_languages_supported

supported_language_keys = [
    "html_code",
    "css_code",
    "js_code",
    "nodejs_code",
    "python_code",
    "react_code",
    "sql_code",
]


def default_css():
    """Return default CSS styles."""
    return """
    body {
        background-color: white;
        font-family: Arial, sans-serif;
        margin: 0;
        padding: 0;
        color: black;
    }
    """


def show_react_help_text():
    with st.expander("Learn More"):
        working_code_sample = """function ToggleButton() {\n  const [isOn, setIsOn] = React.useState(false);\n\n  const toggle = () => {\n    setIsOn(prevState => !prevState);\n  };\n\n  return (\n    <button onClick={toggle}>\n      {isOn ? 'On' : 'Off'}\n    </button>\n  );\n}\n\nconst rootElement = document.getElementById('root');\nReactDOM.render(<ToggleButton />, rootElement);"""
        failing_code_sample = """import React, { useState } from 'react';\n\nfunction ToggleButton() {\n  const [isOn, setIsOn] = useState(false);\n\n  const toggle = () => {\n    setIsOn(prevState => !prevState);\n  };\n\n  return (\n    <button onClick={toggle}>\n      {isOn ? 'On' : 'Off'}\n    </button>\n  );\n}\n\nconst rootElement = document.getElementById('root');\nReactDOM.render(<ToggleButton />, rootElement);"""

        st.markdown(
            f"A few guidelines to follow:\n- Avoid importing `React` or `useState`. Directly use `React.useState` and so on.\n- Structure your code to adhere to the initial code template provided.\n- If your code does not produce the desired output, check if it follows these principles (refer to the example below).\n\nHere is a code sample that produces the desired output.\n\n```jsx\n{working_code_sample}\n```\nBut the following code does not:\n\n```jsx\n{failing_code_sample}\n```"
        )


def show_sql_help_text():
    with st.expander("Learn More"):
        st.markdown(
            "When writing SQL code, **don't forget to add a semicolon (`;`)** at the end of each statement.\n\n"
            "Semicolons are used to **separate multiple SQL statements** so that each one can be recognized and executed independently.\n\n"
            "Without using semicolons, your SQL code might fail or produce unexpected results.\n\n"
            "It's a good habit to always use semicolons to avoid errors when executing multiple SQL commands.\n\n"
            "Avoid adding comments to your code as they will interfere with the execution of your code."
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

    if not css_code:
        css_code = default_css()

    react_template = f"""
    <html>
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>React Test</title>
            <script src="https://unpkg.com/react@18.2.0/umd/react.production.min.js"></script>
            <script src="https://unpkg.com/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
            <script src="https://unpkg.com/babel-standalone/babel.min.js"></script>
            <style>
                {css_code}
            </style>
        </head>
        <body>
            <div id="root"></div>
            <script type="text/babel">
                {jsx_code}
            </script>
        </body>
    </html>
    """
    return react_template


def run_sql_code(code: str) -> list:
    try:
        # Connect to an in-memory SQLite database
        connection = sqlite3.connect(":memory:")
        cursor = connection.cursor()

        # Split the code into individual statements
        statements = re.split(r";\s*", code.strip())
        results = []

        for statement in statements:
            statement = statement.strip()
            if not statement:
                continue

            try:
                cursor.execute(statement)
                # If the statement is a SELECT query, fetch and store results
                if statement.lower().startswith("select"):
                    rows = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    results.append((rows, columns))
                else:
                    # For other statements, commit the changes
                    connection.commit()
            except sqlite3.Error as e:
                return f"SQL Error in statement `{statement}`: {str(e)}"
        return results
    except sqlite3.Error as e:
        return f"SQL Error: {str(e)}"
    finally:
        connection.close()


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
    elif lang == "SQL":
        output = run_sql_code(code)
    else:
        output = "Unsupported language for execution."

    # Display the output
    st.write("### Output")
    if lang == "React":
        components.html(output, width=width, height=height, scrolling=True)
    elif lang == "SQL":
        if isinstance(output, list):
            if not output:
                st.write("No results found.")
                return

            for index, (rows, columns) in enumerate(output):
                if rows and columns:
                    df = pd.DataFrame(rows, columns=columns)
                    st.dataframe(df, width=width, height=height)
                else:
                    st.write(f"Result {index + 1}: No results found or empty columns.")
        else:
            st.text(output)
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

sql_default_code = """
-- Write your SQL queries here; remember to add a 
-- semicolon (`;`) at the end of each statement; 
-- an example is provided below; 
-- remove all the comments before submitting your code

-- create the table
CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, age INTEGER);
-- insert some data
INSERT INTO students (name, age) VALUES ('Alice', 22);
-- query that data
SELECT * FROM students;
"""


def restore_code_snippets(chat_history):
    code_pattern = re.compile(r"```(\w+)\n([\s\S]*?)```")

    for message in reversed(chat_history):
        if not message.get("response_type") == "code":
            continue

        content = message.get("content", "")
        snippets = code_pattern.findall(content)
        if snippets:
            return {
                f"{language.lower()}_code": code.strip() for language, code in snippets
            }

    return {}


def clean_code(code: str):
    return code.strip()


def get_code_for_ai_feedback():
    combined_code = []

    if st.session_state.get("html_code"):
        combined_code.append(f"```html\n{clean_code(st.session_state.html_code)}\n```")

    if st.session_state.get("css_code"):
        combined_code.append(f"```css\n{clean_code(st.session_state.css_code)}\n```")

    if st.session_state.get("js_code"):
        combined_code.append(f"```js\n{clean_code(st.session_state.js_code)}\n```")

    if st.session_state.nodejs_code:
        combined_code.append(f"```js\n{clean_code(st.session_state.nodejs_code)}\n```")

    if st.session_state.python_code:
        combined_code.append(
            f"```python\n{clean_code(st.session_state.python_code)}\n```"
        )
    if st.session_state.react_code:
        combined_code.append(f"```jsx\n{clean_code(st.session_state.react_code)}\n```")
    if st.session_state.sql_code:
        combined_code.append(f"```sql\n{clean_code(st.session_state.sql_code)}\n```")

    return "\n\n".join(combined_code)


def is_any_code_present():
    return bool(
        st.session_state.get("html_code", "")
        or st.session_state.get("css_code", "")
        or st.session_state.get("js_code", "")
        or st.session_state.get("nodejs_code", "")
        or st.session_state.get("python_code", "")
        or st.session_state.get("react_code", "")
        or st.session_state.get("sql_code", "")
    )


def get_html_preview_code():
    if not is_any_code_present():
        return ""

    combined_code = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            {css_code}  <!-- Insert the CSS code here -->
        </style>
    </head>
    <body>
        {html_code}  <!-- Insert the HTML code here -->
        <script>
            {js_code}  <!-- Insert the JavaScript code here -->
        </script>
    </body>
    </html>
    """

    return combined_code.format(
        html_code=st.session_state.html_code,
        css_code=st.session_state.css_code,
        js_code=st.session_state.js_code,
    )


def toggle_show_code_output():
    if not st.session_state.show_code_output and not is_any_code_present():
        return

    st.session_state.show_code_output = not st.session_state.show_code_output
    retain_code()


def retain_code():
    for key in supported_language_keys:
        # avoid checking for st.session_state[key] being not None as it prevents the code
        # from being restored later on when a chat history is restored
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def show_code_editor(
    task: Dict, code_editor_container, set_ai_running, get_ai_feedback_on_code
):
    restored_code_snippets = restore_code_snippets(st.session_state.chat_history)

    for lang, code in restored_code_snippets.items():
        if lang not in st.session_state:
            st.session_state[lang] = code

    if "React" in task["coding_language"] and "react_code" not in st.session_state:
        st.session_state["react_code"] = react_default_code
    if "SQL" in task["coding_language"] and "sql_code" not in st.session_state:
        st.session_state["sql_code"] = sql_default_code

    with code_editor_container:
        for lang in supported_language_keys:
            if lang not in st.session_state:
                st.session_state[lang] = ""

        close_preview_button_col, _, _, submit_button_col = st.columns([2, 1, 1, 1])

        # st.session_state.show_code_output

        if not st.session_state.show_code_output:
            lang_name_to_tab_name = {
                "HTML": "HTML",
                "CSS": "CSS",
                "Javascript": "JS",
                "NodeJS": "NodeJS",
                "Python": "Python",
                "React": "React",
                "SQL": "SQL",
            }
            tab_name_to_language = {
                "HTML": "html",
                "CSS": "css",
                "JS": "javascript",
                "NodeJS": "javascript",
                "Python": "python",
                "React": "jsx",
                "SQL": "sql",
            }
            tab_names = []
            for lang in task["coding_language"]:
                tab_names.append(lang_name_to_tab_name[lang])

            with st.form("Code"):
                st.form_submit_button(
                    "Run Code",
                    on_click=toggle_show_code_output,
                    disabled=st.session_state.is_ai_running,
                )

                tabs = st.tabs(tab_names)
                for index, tab in enumerate(tabs):
                    with tab:
                        tab_name = tab_names[index].lower()
                        language = tab_name_to_language[tab_names[index]]

                        if tab_name == "react":
                            show_react_help_text()
                        elif tab_name == "sql":
                            show_sql_help_text()

                        st_ace(
                            min_lines=15,
                            theme="monokai",
                            language=language,
                            tab_size=2,
                            key=f"{tab_name}_code",
                            auto_update=True,
                            value=st.session_state[f"{tab_name}_code"],
                            placeholder=f"Write your {language} code here...",
                            height=275,
                        )

        else:
            if not task["tests"]:
                output_container = st.container()
            else:
                tab_names = ["Output", f"Tests ({len(task['tests'])})"]
                output_tab, tests_tab = st.tabs(tab_names)
                output_container = output_tab

                with tests_tab:
                    try:
                        test_results = run_tests(
                            st.session_state.python_code, task["tests"]
                        )
                        num_tests = len(task["tests"])
                        num_tests_passed = len(
                            [
                                result
                                for result in test_results
                                if result["status"] == "passed"
                            ]
                        )
                        if num_tests_passed == num_tests:
                            st.success(f"{num_tests_passed}/{num_tests} tests passed")
                        elif num_tests_passed == 0:
                            st.error(f"{num_tests_passed}/{num_tests} tests passed")
                        else:
                            st.warning(f"{num_tests_passed}/{num_tests} tests passed")

                        for i, (test, result) in enumerate(
                            zip(task["tests"], test_results)
                        ):

                            if result["status"] == "passed":
                                expander_icon = f"✅"
                            elif result["status"] == "failed":
                                expander_icon = f"❌"
                            else:  # timeout
                                expander_icon = f"⏳ "

                            expander_label = f"Test Case #{i+1}"

                            if result["status"] == "passed":
                                expander_color = "green"
                            elif result["status"] == "failed":
                                expander_color = "red"
                            else:  # timeout
                                expander_color = "yellow"

                            with st.expander(expander_label, icon=expander_icon):
                                st.markdown("**Inputs**", help=test["description"])
                                for input_text in test["input"]:
                                    st.markdown(input_text)
                                st.write("**Expected Output**")
                                st.write(test["output"])
                                st.write("**Actual Output**")
                                st.write(result["output"])

                    except ValueError as e:
                        st.error(str(e))

            with output_container:
                if any(
                    lang in task["coding_language"]
                    for lang in coding_languages_supported
                ):
                    with st.expander("Configuration"):
                        dim_cols = st.columns(2)
                        height = dim_cols[0].slider(
                            "Preview Height",
                            min_value=100,
                            max_value=1000,
                            value=300,
                            on_change=retain_code,
                        )
                        width = dim_cols[1].slider(
                            "Preview Width",
                            min_value=100,
                            max_value=600,
                            value=600,
                            on_change=retain_code,
                        )

                try:
                    with st.container(border=True):
                        if "HTML" in task["coding_language"]:
                            components.html(
                                get_html_preview_code(),
                                width=width,
                                height=height,
                                scrolling=True,
                            )
                        elif "Javascript" in task["coding_language"]:
                            execute_code(st.session_state.js_code, "Javascript")
                        elif "NodeJS" in task["coding_language"]:
                            execute_code(st.session_state.nodejs_code, "NodeJS")
                        elif "Python" in task["coding_language"]:
                            execute_code(st.session_state.python_code, "Python")
                        elif "React" in task["coding_language"]:
                            execute_code(
                                st.session_state.react_code,
                                "React",
                                width=width,
                                height=height,
                            )
                        elif "SQL" in task["coding_language"]:
                            execute_code(
                                st.session_state.sql_code,
                                "SQL",
                                width=width,
                                height=height,
                            )
                        else:
                            st.write("**No output to show**")
                        # TODO: support for only JS
                        # TODO: support for other languages
                except Exception as e:
                    st.error(f"Error: {e}")

            close_preview_button_col.button(
                "Back to Editor",
                on_click=toggle_show_code_output,
                disabled=st.session_state.is_ai_running,
            )

            if submit_button_col.button(
                "Submit Code",
                type="primary",
                disabled=st.session_state.is_ai_running,
                on_click=set_ai_running,
            ):
                get_ai_feedback_on_code()
