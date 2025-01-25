from typing import List, Optional, Dict, Literal
import pandas as pd
import streamlit as st
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
import instructor
from openai import OpenAI
from lib.ui import display_waiting_indicator
from lib.utils.logging import logger


def show_ai_report(ai_response_rows, column_names):
    display_rows = []

    for row in ai_response_rows:
        if isinstance(row[1], dict):
            display_feedback = f"""✅ {row[1]['correct']}<br>❌ {row[1]['wrong']}"""
        else:
            display_feedback = f"""✅ {row[1].correct}<br>❌ {row[1].wrong}"""

        display_rows.append([row[0], display_feedback, row[2]])

    df = pd.DataFrame(display_rows, columns=column_names)

    st.markdown(
        df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )


def get_ai_report_response(
    ai_chat_history: List[Dict],
    scoring_criteria: List[Dict],
    task_context: str,
    task_type: Literal["audio", "text"],
    api_key: str,
    max_completion_tokens: int = 2048,
):
    display_waiting_indicator()

    if task_type == "audio":
        model = "gpt-4o-audio-preview-2024-12-17"
    else:
        model = "gpt-4o-2024-08-06"

    class Feedback(BaseModel):
        correct: str = Field(description="What worked well")
        wrong: str = Field(description="What needs improvement")

    class Row(BaseModel):
        category: str = Field(description="Category from scoring criteria")
        feedback: Feedback = Field(description="Detailed feedback for this category")
        score: int = Field(
            description="Score given within the min/max range for this category"
        )

    class Output(BaseModel):
        feedback: List[Row] = Field(
            description="List of rows with one row for each category from scoring criteria"
        )

        # @classmethod
        # def validate_score_ranges(cls, value):
        #     for feedback_item in value.feedback:
        #         matching_criterion = next(
        #             (
        #                 criterion
        #                 for criterion in scoring_criteria
        #                 if criterion["category"] == feedback_item.category
        #             ),
        #             None,
        #         )
        #         if not matching_criterion:
        #             raise ValueError(
        #                 f"Category {feedback_item.category} not found in scoring criteria"
        #             )

        #         min_score, max_score = matching_criterion["range"]
        #         if not (min_score <= feedback_item.score <= max_score):
        #             raise ValueError(
        #                 f"Score {feedback_item.score} for category {feedback_item.category} "
        #                 f"must be between {min_score} and {max_score}"
        #             )

        #     return value

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    scoring_criteria_as_prompt = "Scoring Criteria:\n"
    for criterion in scoring_criteria:
        scoring_criteria_as_prompt += f"""- **{criterion['category']}** [min: {criterion['range'][0]}, max: {criterion['range'][1]}]: {criterion['description']}\n"""

    context_instructions = ""
    if task_context:
        context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{task_context}\n```"""

    system_prompt = f"""You are an expert, helpful, encouraging and empathetic coach for a learner.\n\nYou will be given a task description and the conversation history between you and the student.\n\nYou need to provide concise, actionable feedback to the learner along each of the categories mentioned in the scoring criteria below.\n\n{scoring_criteria_as_prompt}{context_instructions}\n\nUse the following principles for responding to the student:\n- Ask thought-provoking, open-ended questions that challenges the student's preconceptions and encourage them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n- Avoid giving feedback using the same words in subsequent messages because that makes the feedback monotonic. Maintain diversity in your feedback and always keep the tone welcoming.\n- If the student's response is not relevant to the task, remain curious and empathetic while playfully nudging them back to the task in your feedback.\n- Include an emoji in every few feedback messages [refer to the history provided to decide if an emoji should be added].\n- No matter how frustrated the student gets or how many times they ask you for the answer, you must never give away the entire answer in one go. Always provide them hints to let them discover the answer step by step on their own.\n\n{format_instructions}"""

    client = instructor.from_openai(OpenAI(api_key=api_key))

    messages = [{"role": "system", "content": system_prompt}] + ai_chat_history

    stream = client.chat.completions.create_partial(
        model=model,
        messages=messages,
        response_model=Output,
        stream=True,
        max_completion_tokens=max_completion_tokens,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=True,
    )

    rows = []
    for val in stream:
        if not val.feedback:
            continue

        for index, topicwise_feedback in enumerate(val.feedback):
            if (
                not topicwise_feedback.category
                or not topicwise_feedback.feedback
                or not topicwise_feedback.feedback.correct
                or not topicwise_feedback.feedback.wrong
                or topicwise_feedback.score is None
            ):
                continue

            if (
                rows
                and len(rows) > index
                and rows[index][0] == topicwise_feedback.category
            ):
                if rows[index][1] != topicwise_feedback.feedback:
                    rows[index][1] = topicwise_feedback.feedback

                if rows[index][2] != topicwise_feedback.score:
                    rows[index][2] = topicwise_feedback.score
            else:
                rows.append(
                    [
                        topicwise_feedback.category,
                        topicwise_feedback.feedback,
                        topicwise_feedback.score,
                    ]
                )

        show_ai_report(rows, ["Category", "Feedback", "Score"])

    for row in rows:
        row[1] = row[1].model_dump()

    logger.info(system_prompt)

    return rows


def reset_displayed_attempt_index():
    st.session_state.displayed_attempt_index = -1


def increase_displayed_attempt_index():
    st.session_state.displayed_attempt_index += 1


def set_display_for_restoring_history():
    if st.session_state.displayed_attempt_index == -1:
        st.session_state.displayed_attempt_index = st.session_state.current_num_attempts


def set_display_for_new_attempt():
    st.session_state.displayed_attempt_index = st.session_state.current_num_attempts


def decrease_displayed_attempt_index():
    st.session_state.displayed_attempt_index -= 1


def reset_current_num_attempts():
    st.session_state.current_num_attempts = 0


def increase_current_num_attempts():
    st.session_state.current_num_attempts += 1


def show_attempt_picker(container):
    cols = container.columns([1, 1, 1, 10])

    with cols[0]:
        st.button(
            "<",
            key="prev_attempt",
            disabled=st.session_state.displayed_attempt_index == 1,
            on_click=decrease_displayed_attempt_index,
        )
    with cols[1]:
        st.markdown(
            f"<div style='text-align: center; margin-left: -10px; margin-top: 5px;'>{st.session_state.displayed_attempt_index}/{st.session_state.current_num_attempts}</div>",
            unsafe_allow_html=True,
        )

    with cols[2]:
        st.button(
            "&gt;",
            key="next_attempt",
            disabled=st.session_state.displayed_attempt_index
            == st.session_state.current_num_attempts,
            on_click=increase_displayed_attempt_index,
        )


def get_containers(is_review_mode: bool):
    input_description_col, _, report_col = st.columns([1, 0.1, 1.5])
    description_container = input_description_col.container(height=450, border=True)

    navigation_container = report_col.container().empty()

    user_input_kwargs = {}
    if not is_review_mode:
        user_input_kwargs = {"height": 100, "border": False}

    user_input_display_container = report_col.container(**user_input_kwargs).empty()

    # for spacing
    report_col.container(height=1, border=False)

    if not is_review_mode:
        report_height = 300 if st.session_state.current_num_attempts > 1 else 250
    else:
        report_height = 500

    ai_report_container = report_col.container(
        border=False, height=report_height
    ).empty()

    return (
        navigation_container,
        description_container,
        user_input_display_container,
        ai_report_container,
    )


def display_user_text_input_report(
    user_input_display_container, user_response: str, is_review_mode: bool = False
):
    container = user_input_display_container.container()

    description = "**Your response**" if not is_review_mode else "**Response**"

    with container:
        st.markdown(f"{description}<br>{user_response}", unsafe_allow_html=True)


def display_user_audio_input_report(
    user_input_display_container, audio_data: bytes, is_review_mode: bool = False
):
    container = user_input_display_container.container()

    description = "**Your response**" if not is_review_mode else "**Response**"

    with container:
        st.markdown(f"{description}", unsafe_allow_html=True)
        st.audio(audio_data)
