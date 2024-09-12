import streamlit as st
import os
from functools import partial

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from openai import OpenAI
# from lib.llm  import get_llm_input_messages,call_llm_and_parse_output
from lib.db import get_task_by_id, store_message as store_message_to_db, get_task_chat_history_for_user, delete_message as delete_message_from_db
from lib.init import init_env_vars
from auth import init_auth_from_cookies

init_env_vars()

init_auth_from_cookies()

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

st.link_button('Open task list', '/task_list')

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

st.write(f"## {task['name']}")
st.text(task['description'].replace('\n', '\n\n'))

# st.session_state

if "chat_history" not in st.session_state:
    st.session_state.chat_history = get_task_chat_history_for_user(task_id, st.session_state.email)


def transform_user_message_for_ai_history(message: dict):
    return {"role": message['role'], "content": f'''Student's response: ```\n{message['content']}\n```'''}


def transform_assistant_message_for_ai_history(message: dict):
    return {"role": message['role'], "content": message['content']}

if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = [{"role": "user", "content": f"""Task:\n```\n{task['description']}\n```\n\nSolution:\n```\n{task['answer']}\n```"""}]
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.session_state.ai_chat_history.append(transform_user_message_for_ai_history(message))
        else:
            st.session_state.ai_chat_history.append(transform_assistant_message_for_ai_history(message))

# st.session_state.ai_chat_history
# st.session_state.chat_history

# st.stop()

def delete_user_chat_message(index_to_delete: int):
    # delete both the user message and the AI assistant's response to it
    updated_chat_history = st.session_state.chat_history[:index_to_delete]
    updated_ai_chat_history = st.session_state.ai_chat_history[:index_to_delete]

    delete_message_from_db(st.session_state.chat_history[index_to_delete]['id']) # delete user message
    delete_message_from_db(st.session_state.chat_history[index_to_delete + 1]['id']) # delete ai message

    if index_to_delete + 2 < len(st.session_state.chat_history):
        updated_chat_history += st.session_state.chat_history[index_to_delete + 2 :]
        updated_ai_chat_history += st.session_state.ai_chat_history[
            index_to_delete + 2 :
        ]

    st.session_state.chat_history = updated_chat_history
    st.session_state.ai_chat_history = updated_ai_chat_history


def display_user_message(user_response: str, message_index: int):
    with st.chat_message("user"):
        user_answer_cols = st.columns([7, 1])
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
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_ai_response():
    # response = random.choice(
    #     [
    #         "Hello there! How can I assist you today?",
    #         "Hi, human! Is there anything I can help you with?",
    #         "Do you need help?",
    #     ]
    # )
    # for word in response.split():
    #     yield word + " "
    #     time.sleep(0.05)

    system_prompt = """You are a Socratic tutor.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nUse the following principles for responding to the student:\n- Ask thought-provoking, open-ended questions that challenges the student's preconceptions and encourage them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n\nImportant Instructions:\n- The student does not have access to the solution. The solution has been provided to you for evaluating the student's response only. Keep this in mind while responding to the student."""

    return client.chat.completions.create(
        model='gpt-4o-2024-08-06',
        messages=[{'role': "system", 'content': system_prompt}] + [
            {"role": message["role"], "content": message["content"]}
            for message in st.session_state.ai_chat_history
        ],
        stream=True,
    )




    # class Output(BaseModel):
    #     solution: str = Field(
    #         title="solution",
    #         description="The solution to the task",
    #     )

    # output_parser = PydanticOutputParser(pydantic_object=Output)

    # llm_input_messages = get_llm_input_messages(
    #     system_prompt_template,
    #     user_prompt_template,
    #     task_description=task['description'],
    #     solution=task['answer'],
    #     student_answer=st.session_state.chat_history[-1]['content'],
    #     # format_instructions=output_parser.get_format_instructions(),
    #     # common_instructions=COMMON_INSTRUCTIONS
    # )

    # try:
    #     pred_dict = asyncio.run(call_llm_and_parse_output(
    #         llm_input_messages,
    #         model='gpt-4o-2024-08-06',
    #         # output_parser=output_parser,
    #         max_tokens=2048,
    #         verbose=True,
    #         # labels=["final_answers", "audit rights"],
    #         # model_type=model_type,
    #     ))
    #     st.session_state.answer = pred_dict['solution']
    # except Exception as exception:
    #     traceback.print_exc()
    #     raise Exception



if user_response := st.chat_input("Your response"):
    display_user_message(user_response, len(st.session_state.chat_history))
    
    user_message = {'role': 'user', 'content': user_response}
    st.session_state.chat_history.append(user_message)
    st.session_state.ai_chat_history.append(transform_user_message_for_ai_history(user_message))

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        ai_response = st.write_stream(get_ai_response())

    # Add user message to chat history [store to db only if ai response has been completely fetched]
    new_user_message = store_message_to_db(st.session_state.email, task_id, "user", user_response)
    st.session_state.chat_history[-1] = new_user_message

    # Add assistant response to chat history
    new_ai_message = store_message_to_db(st.session_state.email, task_id, "assistant", ai_response)
    st.session_state.chat_history.append(new_ai_message)
    st.session_state.ai_chat_history.append(transform_assistant_message_for_ai_history(new_ai_message))

    st.rerun()


