import streamlit as st
from typing import List, Dict
from pydantic import BaseModel, Field
import instructor
import openai
from langchain.output_parsers import PydanticOutputParser
from lib.db import delete_message as delete_message_from_db
from lib.ui import display_waiting_indicator, cleanup_ai_response
from lib.llm import logger


def delete_user_chat_message(index_to_delete: int):
    # NOTE:
    # We removed support for deleting chat message as it messes up the streak calculation

    # delete both the user message and the AI assistant's response to it
    updated_chat_history = st.session_state.chat_history[:index_to_delete]
    current_ai_chat_history = st.session_state.ai_chat_history.messages
    # import ipdb; ipdb.set_trace()
    ai_chat_index_to_delete = (
        index_to_delete + 1
    )  # since we have an extra message in ai_chat_history at the start
    updated_ai_chat_history = current_ai_chat_history[:ai_chat_index_to_delete]

    delete_message_from_db(
        st.session_state.chat_history[index_to_delete]["id"]
    )  # delete user message
    delete_message_from_db(
        st.session_state.chat_history[index_to_delete + 1]["id"]
    )  # delete ai message

    if index_to_delete + 2 < len(st.session_state.chat_history):
        updated_chat_history += st.session_state.chat_history[index_to_delete + 2 :]
        updated_ai_chat_history += current_ai_chat_history[
            ai_chat_index_to_delete + 2 :
        ]

    st.session_state.chat_history = updated_chat_history
    st.session_state.ai_chat_history.clear()
    st.session_state.ai_chat_history.add_messages(updated_ai_chat_history)


def get_containers(task, is_review_mode):
    if task["type"] == "coding" and not is_review_mode:
        chat_column, code_column = st.columns(2)
        description_container = chat_column.container(height=200)
        chat_container = chat_column.container(height=325)

        code_input_container = code_column.container(height=475, border=False)
        chat_input_container = code_column.container(height=100, border=False)

        return (
            description_container,
            chat_container,
            chat_input_container,
            code_input_container,
        )

    # chat_column = st.columns(1)[0]
    description_col, chat_col = st.columns(2)

    description_container = description_col.container(height=450, border=True)
    chat_container = chat_col.container(border=True, height=450)

    chat_input_container = None

    return description_container, chat_container, chat_input_container


def display_user_chat_message(chat_container, user_response: str):
    with chat_container.chat_message("user"):
        st.markdown(user_response, unsafe_allow_html=True)


def get_ai_chat_response(
    ai_chat_history: List[Dict], response_type: str, task_context: str, container
):
    with container.chat_message("assistant"):
        ai_response_container = st.empty()

    with ai_response_container:
        display_waiting_indicator()

    client = instructor.from_openai(openai.OpenAI())

    class Output(BaseModel):
        analysis: str = Field(description="Analysis of the student's response")
        if response_type == "chat":
            feedback: List[str] = Field(
                description="Feedback on the student's response; return each word as a separate element in the list; add newline characters to the feedback to make it more readable"
            )
        is_correct: bool = Field(
            description="Whether the student's response correctly solves the task given to the student"
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    # print(format_instructions)

    context_instructions = ""
    if task_context:
        context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{task_context}\n```"""

    if response_type == "exam":
        system_prompt = f"""You are a grader responsible for grading the response of a student for a task.\n\nYou will be given the task description, its solution and the response given by the student.\n\nYou need to tell whether the student's response is correct or not.{context_instructions}\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description, reference solution and compare the student's response with the solution.\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""
    else:
        system_prompt = f"""You are a Socratic tutor.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nUse the following principles for responding to the student:\n- Ask thought-provoking, open-ended questions that challenges the student's preconceptions and encourage them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n- Avoid giving feedback using the same words in subsequent messages because that makes the feedback monotonic. Maintain diversity in your feedback and always keep the tone welcoming.\n- If the student's response is not relevant to the task, remain curious and empathetic while playfully nudging them back to the task in your feedback.\n- Include an emoji in every few feedback messages [refer to the history provided to decide if an emoji should be added].\n- If the task resolves around code, use backticks ("`", "```") to format sections of code or variable/function names in your feedback.\n- No matter how frustrated the student gets or how many times they ask you for the answer, you must never give away the entire answer in one go. Always provide them hints to let them discover the answer step by step on their own.{context_instructions}\n\nImportant Instructions:\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n- Whenever you include any html in your feedback, make sure that the html tags are enclosed within backticks (i.e. `<html>` instead of <html>).\n\n{format_instructions}"""

    model = "gpt-4o-2024-08-06"

    messages = [{"role": "system", "content": system_prompt}] + ai_chat_history

    stream = client.chat.completions.create_partial(
        model=model,
        messages=messages,
        response_model=Output,
        stream=True,
        max_completion_tokens=2048,
        top_p=1,
        temperature=0,
        frequency_penalty=0,
        presence_penalty=0,
        store=True,
    )

    ai_response = None

    for extraction in stream:
        # print(extraction)
        result_dict = extraction.model_dump()
        if response_type == "exam":
            continue

        ai_response_list = result_dict["feedback"]
        if ai_response_list:
            ai_response = " ".join(ai_response_list)
            ai_response_container.markdown(
                cleanup_ai_response(ai_response), unsafe_allow_html=True
            )

    logger.info(system_prompt)

    # import ipdb

    # ipdb.set_trace()

    return ai_response, result_dict
