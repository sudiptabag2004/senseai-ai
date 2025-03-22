import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, AsyncGenerator
import json
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from api.config import openai_plan_to_model_name
from api.models import TaskAIResponseType, AIChatRequest, ChatResponseType
from api.llm import run_llm_with_instructor, stream_llm_with_instructor
from api.settings import settings
from api.utils.logging import logger
from api.db import (
    get_question_chat_history_for_user,
    get_question,
    construct_description_from_blocks,
)
from api.utils.s3 import download_file_from_s3_as_bytes, get_audio_upload_s3_key
from api.utils.audio import prepare_audio_input_for_ai

router = APIRouter()


@router.post("/chat")
async def ai_response_for_question(request: AIChatRequest):
    if request.question_id is None and request.question is None:
        raise HTTPException(
            status_code=400, detail="Question ID or question is required"
        )

    if request.question_id is not None and request.user_id is None:
        raise HTTPException(
            status_code=400,
            detail="User ID is required when question ID is provided",
        )

    if request.question and request.chat_history is None:
        raise HTTPException(
            status_code=400,
            detail="Chat history is required when question is provided",
        )

    if request.question_id:
        question = await get_question(request.question_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        chat_history = await get_question_chat_history_for_user(
            request.question_id, request.user_id
        )
        # TODO: account for audio in history
        chat_history = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in chat_history
        ]
    else:
        question = request.question.model_dump()
        # TODO: account for audio in history
        chat_history = request.chat_history

    question_description = construct_description_from_blocks(question["blocks"])
    question_details = f"""Task:\n```\n{question_description}\n```"""

    if request.response_type == ChatResponseType.AUDIO:
        audio_data = download_file_from_s3_as_bytes(
            get_audio_upload_s3_key(request.user_response)
        )

        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": prepare_audio_input_for_ai(audio_data),
                        "format": "wav",
                    },
                },
            ],
        }
    else:
        user_message = {"role": "user", "content": request.user_response}

    if question["response_type"] in [TaskAIResponseType.CHAT, TaskAIResponseType.EXAM]:
        question_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{question['answer']}\n```"""

    chat_history = (
        [
            {
                "role": "user",
                "content": question_details,
            }
        ]
        + chat_history
        + [user_message]
    )

    class Output(BaseModel):
        if question["response_type"] == TaskAIResponseType.CHAT:
            feedback: str = Field(
                description="Feedback on the student's response; add newline characters to the feedback to make it more readable where necessary"
            )
        is_correct: bool = Field(
            description="Whether the student's response correctly solves the task that the student is supposed to solve. For this to be true, the task needs to be completely solved and not just partially solved."
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    # context_instructions = ""
    # if request.task_context:
    #     context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{request.task_context}\n```"""

    if question["response_type"] in [
        TaskAIResponseType.EXAM,
    ]:
        system_prompt = f"""You are a grader responsible for grading the response of a student for a task.\n\nYou will be given the task description, its solution and the response given by the student.\n\nYou need to tell whether the student's response is correct or not.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description, reference solution and compare the student's response with the solution.\n\n{format_instructions}"""
    else:
        system_prompt = f"""You are a Socratic tutor.\n\nYou will receive:\n- Task description\n- Task solution (for your reference only; do not reveal)\n- Conversation history with the student\n\nYour role:\n- Engage students with open-ended questions to encourage deep reflection and critical thinking.\n- Foster a respectful, welcoming dialogue; value diverse viewpoints.\n- Listen actively, paying attention to the student's reasoning and thought process.\n- Encourage students to independently discover answers; you can never ever provide direct answers or explanations.\n- Prompt students to question assumptions, assess evidence, and explore alternative perspectives.\n- Maintain humility, acknowledge uncertainties, and model lifelong learning.\n- Never provide complete solutions outright, regardless of student frustration; guide them step-by-step.\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n\nGuidelines on your feedback style:\n- Vary your phrasing to avoid monotony; occasionally include emojis to maintain warmth and engagement.\n- Playfully redirect irrelevant responses back to the task without judgment.\n- If the task involves code, format code snippets or variable/function names with backticks (`example`).\n- If including HTML, wrap tags in backticks (`<html>`).\n- Your role is that of a tutor only. Remember that and avoid steering the conversation in any other direction apart from the actual task at hand.\n- Ask only one reflective question per response otherwise the learner will get overwhelmed.\n- Avoid being unnecessarily verbose in your feedback.\n\nGuidelines on assessing correctness of the student's answer:\n- Once the student has provided an answer that is correct with respect to the solution provided at the start, clearly acknowledge that they have got the correct answer and stop asking any more reflective questions. Your response should make them feel a sense of completion and accomplishment at a job well done.\n- If the question is a subjective type question where the answer does not need to match word-for-word with the solution, only assess whether the student's answer covers the entire essence of the correct solution.\n- Avoid bringing in your judgement of what the right answer should be. What matters for evaluation is the solution provided to you and the response of the student. Keep your biases outside. Be objective in comparing these two. As soon as the learner gets the answer correct, stop asking any further reflective questions.\n- The student might get the answer right without any probing required from your side in the first couple of attempts itself. In that case, remember the instruction provided above to acknowledge their answer's correctness and to stop asking further questions.\n\n{format_instructions}"""

    if request.response_type == ChatResponseType.AUDIO:
        model = openai_plan_to_model_name["audio"]
    else:
        model = openai_plan_to_model_name["reasoning"]

    messages = [{"role": "system", "content": system_prompt}] + chat_history

    try:
        # Define an async generator for streaming
        async def stream_response() -> AsyncGenerator[str, None]:
            stream = stream_llm_with_instructor(
                api_key=settings.openai_api_key,
                model=model,
                messages=messages,
                response_model=Output,
                max_completion_tokens=4096,
            )

            # Since stream is a regular generator, not an async generator,
            # we need to iterate over it differently
            for chunk in stream:
                yield json.dumps(chunk.model_dump()) + "\n"

        # Return a streaming response
        return StreamingResponse(
            stream_response(),
            media_type="application/x-ndjson",
        )

    except Exception as exception:
        logger.error(exception)
        raise exception
