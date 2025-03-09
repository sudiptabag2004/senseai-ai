import streamlit as st
from typing import List, Dict
from pydantic import BaseModel, Field
import backoff
from langchain.output_parsers import PydanticOutputParser
from lib.ui import display_waiting_indicator, cleanup_ai_response
from lib.utils.logging import logger
from models import TaskAIResponseType
from lib.config import openai_plan_to_model_name
from lib.llm import stream_llm_with_instructor


def get_containers(task, is_review_mode):
    if task["input_type"] == "coding" and not is_review_mode:
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

    description_container = description_col.container(height=475, border=True)
    chat_container = chat_col.container(border=True, height=475)

    chat_input_container = st.container(height=50, border=False)

    return description_container, chat_container, chat_input_container


def display_user_chat_message(chat_container, user_response: str):
    with chat_container.chat_message("user"):
        st.markdown(user_response, unsafe_allow_html=True)


@backoff.on_exception(backoff.expo, Exception, max_tries=5, factor=2)
def get_ai_chat_response(
    ai_chat_history: List[Dict],
    response_type: str,
    task_context: str,
    api_key: str,
):
    display_waiting_indicator()

    class Output(BaseModel):
        analysis: str = Field(description="Analysis of the student's response")
        if response_type == "chat":
            feedback: str = Field(
                description="Feedback on the student's response; add newline characters to the feedback to make it more readable where necessary"
            )
        is_correct: bool = Field(
            description="Whether the student's response correctly solves the task that the student is supposed to solve"
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    # print(format_instructions)

    context_instructions = ""
    if task_context:
        context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{task_context}\n```"""

    if response_type in [
        TaskAIResponseType.EXAM,
    ]:
        system_prompt = f"""You are a grader responsible for grading the response of a student for a task.\n\nYou will be given the task description, its solution and the response given by the student.\n\nYou need to tell whether the student's response is correct or not.{context_instructions}\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description, reference solution and compare the student's response with the solution.\n\n{format_instructions}"""
    else:
        system_prompt = f"""You are a Socratic tutor.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nImportant Instructions for the style of the feedback:\n- Ask a thought-provoking, open-ended question that challenges the student's preconceptions and encourages them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills.\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n- Avoid giving feedback using the same words in subsequent messages because that makes the feedback monotonic. Maintain diversity in your feedback and always keep the tone welcoming.\n- If the student's response is not relevant to the task, remain curious and empathetic while playfully nudging them back to the task in your feedback.\n- Include an emoji in every few feedback messages [refer to the history provided to decide if an emoji should be added].\n- If the task resolves around code, use backticks ("`", "```") to format sections of code or variable/function names in your feedback.\n- No matter how frustrated the student gets or how many times they ask you for the answer, you must never give away the entire answer in one go. Always provide them hints to let them discover the answer step by step on their own.{context_instructions}\n\nImportant Instructions for the content of the feedback:\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n- Whenever you include any html in your feedback, make sure that the html tags are enclosed within backticks (i.e. `<html>` instead of <html>).\n- Make sure to adhere to the style instructions strictly. The tone of your response matters a lot.\n- Your role is that of a tutor only. Remember that and avoid steering the conversation in any other direction apart from the actual task at hand.\n- Never overwhelm the learner with more than one question at a time.\n\n{format_instructions}"""

    model = openai_plan_to_model_name["reasoning"]

    messages = [{"role": "system", "content": system_prompt}] + ai_chat_history

    while True:
        ai_response = None
        result_dict = None

        try:
            stream = stream_llm_with_instructor(
                api_key=api_key,
                model=model,
                messages=messages,
                response_model=Output,
                max_completion_tokens=4096,
            )

            for extraction in stream:
                result_dict = extraction.model_dump()
                if response_type in [
                    TaskAIResponseType.EXAM,
                ]:
                    continue

                if not result_dict["feedback"]:
                    continue

                ai_response = result_dict["feedback"]
                st.markdown(ai_response, unsafe_allow_html=True)

            logger.info(f"model: {model} prompt: {messages} response: {result_dict}")

            if response_type in [
                TaskAIResponseType.EXAM,
            ] or (response_type == TaskAIResponseType.CHAT and ai_response):
                break

            logger.info("AI feedback empty. Retrying...")

        except Exception as exception:
            if "insufficient_quota" in str(exception):
                st.error(
                    "Notify your admin that their OpenAI account credits have been exhausted. Please ask them to recharge their OpenAI account for you to continue using SensAI."
                )
                st.stop()

            logger.error(exception)
            raise exception

    # import ipdb

    # ipdb.set_trace()

    return ai_response, result_dict


def show_response_limit_exceeded_message():
    message_html = """
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
    ">
    
    <div style="
        display: inline-block;
        padding: 10px 20px;
        background-color: #ff4b4b;
        color: white;
        border-radius: 8px;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
        margin: auto;
    ">
        You have reached the maximum number of attempts!
    </div>
    """
    st.markdown(message_html, unsafe_allow_html=True)


def show_attempts_status(user_attempts, max_attempts):
    status_html = f"""
    <div style="
        display: flex;
        justify-content: center;
        align-items: center;
    ">
    <div style="
        display: inline-block;
        padding: 5px 10px;
        margin: auto;
        background-color: #007BFA;
        color: white;
        border-radius: 5px;
        font-size: 18px;
        font-weight: bold;
        text-align: center;
    ">
        {user_attempts}/{max_attempts} attempts used
    </div>
    """
    st.markdown(status_html, unsafe_allow_html=True)


def is_response_limit_exceeded(task):
    if not task["max_attempts"]:
        return False

    user_attempts = len(st.session_state.chat_history) // 2
    return user_attempts >= task["max_attempts"]
