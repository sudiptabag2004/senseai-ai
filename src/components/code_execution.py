from typing import List, Dict, Tuple
import subprocess
import tempfile
import re
import streamlit as st
import asyncio
import json


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
        replacement = f"'{inputs[i]}'"
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
            code = replace_inputs_in_code(
                code,
                user_input_instances,
                [
                    st.session_state[f"input_{i}"]
                    for i in range(len(user_input_instances))
                ],
            )

            # print(code)

        output = asyncio.run(run_python_code_with_timeout(code))
    else:
        output = "Unsupported language for execution."

    # Display the output
    st.write("### Output")
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
