from typing import Literal
import os
import time
import json
from functools import partial
import asyncio
from pydantic import BaseModel, Field
from openai import OpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.chat_history import (
    InMemoryChatMessageHistory,
)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables.history import RunnableWithMessageHistory

import streamlit as st
st.set_page_config(layout="wide")

from streamlit_ace import st_ace, THEMES

# from lib.llm  import get_llm_input_messages,call_llm_and_parse_output
from components.sticky_container import sticky_container
from lib.db import get_task_by_id, store_message as store_message_to_db, get_task_chat_history_for_user, delete_message as delete_message_from_db
from lib.init import init_env_vars, init_db

init_env_vars()
init_db()

st.markdown("""
<style>
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            padding-left: 5rem;
            padding-right: 5rem;
        }
</style>
""", unsafe_allow_html=True)


if 'email' not in st.query_params:
    st.error('Not authorized. Redirecting to home page...')
    time.sleep(2)
    st.switch_page('./home.py')

st.session_state.email = st.query_params['email']

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

task_id = st.query_params.get('id')

if not task_id:
    st.error('No task id provided')
    st.stop()

try:
    task_index = int(task_id)
except ValueError:
    st.error('Task index must be an integer')
    st.stop()

task = get_task_by_id(task_id)

if not task:
    st.error('No task found')
    st.stop()

if not task['verified']:
    st.error('Task not verified. Please ask your mentor/teacher to verify the task so that you can solve it.')
    st.stop()


if "chat_history" not in st.session_state:
    st.session_state.chat_history = get_task_chat_history_for_user(task_id, st.session_state.email)

if 'is_solved' not in st.session_state:
    st.session_state.is_solved = len(st.session_state.chat_history) and st.session_state.chat_history[-2]['is_solved']

task_name_container_background_color = None
task_name_container_text_color = None
if st.session_state.is_solved:
    task_name_container_background_color = '#62B670'
    task_name_container_text_color = 'white'

with sticky_container(mode="top", border=True, background_color=task_name_container_background_color, text_color=task_name_container_text_color):
    # st.link_button('Open task list', '/task_list')

    heading = f"**{task['name']}**"
    if st.session_state.is_solved:
        heading += " ✅"
    st.write(heading)

    with st.expander("Task description", expanded=False):
        st.text(task['description'].replace('\n', '\n\n'))

# st.session_state
# st.session_state['code']

if task['type'] == 'coding':
    chat_column, code_column = st.columns([5, 5])
    chat_container = chat_column.container(height=450)
    chat_input_container = chat_column.container(height=100, border=False)
else:
    # chat_column = st.columns(1)[0]
    chat_container = st.container()
    chat_input_container = None

def transform_user_message_for_ai_history(message: dict):
    # return {"role": message['role'], "content": f'''Student's response: ```\n{message['content']}\n```'''}
    return HumanMessage(content=f'''Student's response: ```\n{message['content']}\n```''')


def transform_assistant_message_for_ai_history(message: dict):
    # return {"role": message['role'], "content": message['content']}
    return AIMessage(content=message['content'])


if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = InMemoryChatMessageHistory()
    st.session_state.ai_chat_history.add_user_message(f"""Task:\n```\n{task['description']}\n```\n\nSolution:\n```\n{task['answer']}\n```""")

    # st.session_state.ai_chat_history = [{"role": "user", "content": f"""Task:\n```\n{task['description']}\n```\n\nSolution:\n```\n{task['answer']}\n```"""}]
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.session_state.ai_chat_history.add_user_message(transform_user_message_for_ai_history(message))
        else:
            st.session_state.ai_chat_history.add_ai_message(transform_assistant_message_for_ai_history(message))

# st.session_state.ai_chat_history
# st.session_state.chat_history

# st.stop()

def delete_user_chat_message(index_to_delete: int):
    # delete both the user message and the AI assistant's response to it
    updated_chat_history = st.session_state.chat_history[:index_to_delete]
    current_ai_chat_history = st.session_state.ai_chat_history.messages
    # import ipdb; ipdb.set_trace()
    ai_chat_index_to_delete = index_to_delete + 1 # since we have an extra message in ai_chat_history at the start
    updated_ai_chat_history = current_ai_chat_history[:ai_chat_index_to_delete]

    delete_message_from_db(st.session_state.chat_history[index_to_delete]['id']) # delete user message
    delete_message_from_db(st.session_state.chat_history[index_to_delete + 1]['id']) # delete ai message

    if index_to_delete + 2 < len(st.session_state.chat_history):
        updated_chat_history += st.session_state.chat_history[index_to_delete + 2 :]
        updated_ai_chat_history += current_ai_chat_history[
            ai_chat_index_to_delete + 2 :
        ]

    st.session_state.chat_history = updated_chat_history
    st.session_state.ai_chat_history.clear()
    st.session_state.ai_chat_history.add_messages(updated_ai_chat_history)


def display_user_message(user_response: str, message_index: int):
    with chat_container.chat_message("user"):
        user_answer_cols = st.columns([5, 1])
        user_answer_cols[0].markdown(user_response)
        user_answer_cols[1].button(
            "Delete",
            on_click=partial(
                delete_user_chat_message, index_to_delete=message_index
            ),
            key=f'message_{message_index}',
        )

# st.session_state.chat_history
# st.session_state.ai_chat_history

# Display chat messages from history on app rerun
for index, message in enumerate(st.session_state.chat_history):
    if message['role'] == 'user':
        display_user_message(message['content'], message_index=index)
    else:
        with chat_container.chat_message(message["role"]):
            st.markdown(message["content"])


def get_session_history():
    return st.session_state.ai_chat_history


async def _extract_feedback(input_stream):
    """A function that operates on input streams."""
    # feedback = ""
    async for input in input_stream:
        if not isinstance(input, dict):
            continue

        if "feedback" not in input:
            continue
        
        if "is_solved" in input:
            if not isinstance(input["is_solved"], bool):
                continue

            yield json.dumps({'is_solved': input["is_solved"]})

        feedback = input["feedback"]

        if not isinstance(feedback, str):
            continue
    
        # print(feedback)

        yield feedback


async def get_ai_response(user_message: str):
    class Output(BaseModel):
        feedback: str = Field(description="Feedback on the student's response")
        is_solved: bool = Field(description="Whether the student's response correctly solves the task")

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    system_prompt = """You are a Socratic tutor who responds only in JSON.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nUse the following principles for responding to the student:\n- Ask thought-provoking, open-ended questions that challenges the student's preconceptions and encourage them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n\nImportant Instructions:\n- The student does not have access to the solution. The solution has been provided to you for evaluating the student's response only. Keep this in mind while responding to the student.\n\n{format_instructions}."""

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
    ]).partial(format_instructions=format_instructions)

    model = ChatOpenAI(model='gpt-4o-2024-08-06', temperature=0, top_p=1, frequency_penalty=0, presence_penalty=0, verbose=True)

    chain = prompt_template | model | JsonOutputParser() | _extract_feedback

    with_message_history = RunnableWithMessageHistory(chain, get_session_history)

    async for chunk in with_message_history.astream({
        "messages": [transform_user_message_for_ai_history(user_message)]
    }):
        yield chunk
    # response = await with_message_history.ainvoke({
    #     "messages": [transform_user_message_for_ai_history(user_message)]
    # })
    # import ipdb; ipdb.set_trace()
    # return response


def sync_generator(async_gen):
    loop = asyncio.new_event_loop()
    try:
        while True:
            yield loop.run_until_complete(async_gen.__anext__())
    except StopAsyncIteration:
        pass
    finally:
        loop.close()


def get_ai_feedback(user_response: str):
    # import ipdb; ipdb.set_trace()
    display_user_message(user_response, len(st.session_state.chat_history))
    
    user_message = {'role': 'user', 'content': user_response}
    st.session_state.chat_history.append(user_message)
    # st.session_state.ai_chat_history.add_user_message(transform_user_message_for_ai_history(user_message))

    # ipdb.set_trace()

    # Display assistant response in chat message container
    with chat_container.chat_message("assistant"):
        ai_response_container = st.empty()
        for chunk in sync_generator(get_ai_response(user_message)):
            if "is_solved" not in chunk:
                ai_response = chunk
                ai_response_container.write(ai_response)
            else:
                # print(chunk)
                is_solved = json.loads(chunk)['is_solved']
                if not st.session_state.is_solved and is_solved:
                    st.balloons()
                    st.session_state.is_solved = True
                    time.sleep(2)

        # ai_response = st.write_stream(sync_generator(get_ai_response(user_message)))
        # ai_response = asyncio.run(get_ai_response(user_message))
    
    st.session_state.ai_chat_history.messages[-1].content = ai_response

    # st.session_state.chat_history.append(ai_response)
    # Add user message to chat history [store to db only if ai response has been completely fetched]
    new_user_message = store_message_to_db(st.session_state.email, task_id, "user", user_response, st.session_state.is_solved)
    st.session_state.chat_history[-1] = new_user_message

    # Add assistant response to chat history
    new_ai_message = store_message_to_db(st.session_state.email, task_id, "assistant", ai_response)
    st.session_state.chat_history.append(new_ai_message)
    # st.session_state.ai_chat_history.add_ai_message(transform_assistant_message_for_ai_history(new_ai_message))

    st.rerun()

# st.session_state.ai_chat_history
# st.session_state.is_solved

supported_language_keys = ['html_code', 'css_code', 'js_code']

def retain_code():
    for key in supported_language_keys:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


def is_any_code_present():
    return bool(st.session_state.get('html_code', '') or st.session_state.get('css_code', '') or st.session_state.get('js_code', ''))


def get_preview_code():
    if not is_any_code_present():
        return ''

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

    return combined_code.format(html_code=st.session_state.html_code, css_code=st.session_state.css_code, js_code=st.session_state.js_code)

def get_code_for_ai_feedback():
    combined_code = f"`HTML`\n\n{st.session_state.html_code}"

    if st.session_state.css_code:
        # CSS code will always come with HTML code
        combined_code += f"\n\n`CSS`\n\n{st.session_state.css_code}"

    if st.session_state.js_code:
        if task['show_code_preview']:
            # JS code will always come with HTML and CSS code when preview mode is enabled
            combined_code += f"\n\n`JS`\n\n{st.session_state.js_code}"
        else:
            # JS code will be submitted as a standalone message when preview mode is disabled
            combined_code = f"{st.session_state.js_code}"

    # combined_code = combined_code.replace('`', '\`').replace('{', '\{').replace('}', '\}').replace('$', '\$')
    # combined_code = f'`{combined_code}`'
    return combined_code

def get_ai_feedback_on_code():
    get_ai_feedback(get_code_for_ai_feedback())


if 'show_code_output' not in st.session_state:
    st.session_state.show_code_output = False

def toggle_show_code_output():
    st.session_state.show_code_output = not st.session_state.show_code_output
    retain_code()

if task['type'] == 'coding':
    with code_column:
        for lang in supported_language_keys:
            if lang not in st.session_state:
                st.session_state[lang] = ''
        
        close_preview_button_col, _, _, submit_button_col = st.columns([2, 1, 1, 1])

        if not st.session_state.show_code_output:
            tab_name_to_language = {
                'HTML': 'html',
                'CSS': 'css',
                'JS': 'javascript'
            }
            if task['coding_language'] == 'HTML':
                tab_names = ['HTML']
            elif task['coding_language'] == 'CSS':
                tab_names = ['HTML', 'CSS']
            elif task['coding_language'] == 'Javascript':
                if task['show_code_preview']:
                    tab_names = ['HTML', 'CSS', 'JS']
                else:
                    tab_names = ['JS']

            
            with st.form('Code'):
                st.form_submit_button("Run Code", on_click=toggle_show_code_output)

                tabs = st.tabs(tab_names)
                for index, tab in enumerate(tabs):
                    with tab:
                        tab_name = tab_names[index].lower()
                        language = tab_name_to_language[tab_names[index]]
                        st_ace(min_lines=15, theme='monokai', language=language, tab_size=2, key=f'{tab_name}_code', auto_update=True, value=st.session_state[f'{tab_name}_code'], placeholder=f"Write your {language} code here...",)

        else:
            import streamlit.components.v1 as components
            with st.expander("Configuration"):
                dim_cols = st.columns(2)
                height = dim_cols[0].slider('Preview Height', min_value=100, max_value=1000, value=300, on_change=retain_code)
                width = dim_cols[1].slider('Preview Width', min_value=100, max_value=600, value=600, on_change=retain_code)

            try:
                # Render the HTML code in Streamlit using components.v1.html
                with st.container(border=True):
                    # st.write(f'`{get_preview_code()}`')
                    
                    components.html(get_preview_code(), width=width, height=height, scrolling=True)
            except Exception as e:
                st.error(f"Error: {e}")

            close_preview_button_col.button("Back to Editor", on_click=toggle_show_code_output)

        if submit_button_col.button("Submit Code", type='primary'):
            get_ai_feedback_on_code()

        

user_response_placeholder = 'Your response'

if task['type'] == 'coding':
    user_response_placeholder = 'Use the code editor for submitting code and ask/tell anything else here'
else:
    user_response_placeholder = 'Write your response here'
# st.session_state.js_code


def show_and_handle_chat_input():
    if user_response := st.chat_input(user_response_placeholder):
        get_ai_feedback(user_response)

if chat_input_container:
    with chat_input_container:
        show_and_handle_chat_input()
else:
    show_and_handle_chat_input()

# def get_default_chat_input_value():
#     if not is_any_code_present():
#         return '``'

#     combined_code = f"HTML\n\n{st.session_state.html_code}"

#     if st.session_state.css_code:
#         combined_code += f"\n\nCSS\n\n{st.session_state.css_code}"

#     # st.session_state.js_code

#     if st.session_state.js_code:
#         if task['show_code_preview']:
#             combined_code += f"\n\nJS\n\n{st.session_state.js_code}"
#         else:
#             combined_code = f"{st.session_state.js_code}"

#     combined_code = combined_code.replace('`', '\`').replace('{', '\{').replace('}', '\}').replace('$', '\$')
#     combined_code = f'`{combined_code}`'

#     return combined_code

# st.write(default_chat_input_value)

# default_chat_input_value = get_default_chat_input_value()
# # default_chat_input_value = "`Default value`"
# # default_chat_input_value = """`<h1>Hello, World!</h1>
# # <p>This is a live HTML preview with CSS and JavaScript.</p>
# # <button onclick="changeText()">Click Me</button>`"""
# # st.write(default_chat_input_value)

# # if default_chat_input_value:
# # print(default_chat_input_value)
# js = f"""
#     <script>
#         function insertText(dummy_var_to_force_repeat_execution) {{
#             var chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
#             var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
#             nativeInputValueSetter.call(chatInput, {default_chat_input_value});
#             var event = new Event('input', {{ bubbles: true}});
#             chatInput.dispatchEvent(event);
#         }}
#         insertText({len(st.session_state.chat_history)});
#     </script>
#     """
# st.components.v1.html(js, height=0)
    # st.markdown(js, unsafe_allow_html=True)
