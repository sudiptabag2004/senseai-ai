from fastapi import APIRouter, HTTPException
from typing import Dict
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from api.config import openai_plan_to_model_name
from api.models import TaskAIResponseType, AIChatRequest, TaskType
from api.llm import run_llm_with_instructor
from api.settings import settings
from api.utils.logging import logger
from api.db import (
    get_question_chat_history_for_user,
    get_question,
    construct_description_from_blocks,
)

router = APIRouter()


@router.post("/chat")
async def ai_response_for_question(request: AIChatRequest) -> Dict:
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
        chat_history = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in chat_history
        ]
    else:
        question = request.question.model_dump()
        chat_history = request.chat_history

    question_description = construct_description_from_blocks(question["blocks"])
    question_details = f"""Task:\n```\n{question_description}\n```"""

    chat_history = (
        [
            {
                "role": "user",
                "content": question_details,
            }
        ]
        + chat_history
        + [
            {
                "role": "user",
                "content": request.user_response,
            }
        ]
    )

    if question["response_type"] in [TaskAIResponseType.CHAT, TaskAIResponseType.EXAM]:
        question_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{question['answer']}\n```"""

    class Output(BaseModel):
        analysis: str = Field(description="Analysis of the student's response")
        if question["response_type"] == TaskAIResponseType.CHAT:
            feedback: str = Field(
                description="Feedback on the student's response; add newline characters to the feedback to make it more readable where necessary"
            )
        is_correct: bool = Field(
            description="Whether the student's response correctly solves the task that the student is supposed to solve. For this to be true, the task needs to be completely solved and not just partially solved."
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    context_instructions = ""
    # if request.task_context:
    #     context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{request.task_context}\n```"""

    if question["response_type"] in [
        TaskAIResponseType.EXAM,
    ]:
        system_prompt = f"""You are a grader responsible for grading the response of a student for a task.\n\nYou will be given the task description, its solution and the response given by the student.\n\nYou need to tell whether the student's response is correct or not.{context_instructions}\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description, reference solution and compare the student's response with the solution.\n\n{format_instructions}"""
    else:
        system_prompt = f"""You are a Socratic tutor.\n\nYou will be given a task description, its solution and the conversation history between you and the student.\n\nImportant Instructions for the style of the feedback:\n- Ask a thought-provoking, open-ended question that challenges the student's preconceptions and encourages them to engage in deeper reflection and critical thinking.\n- Facilitate open and respectful dialogue with the student, creating an environment where diverse viewpoints are valued and the student feels comfortable sharing their ideas.\n- Actively listen to the student's responses, paying careful attention to their underlying thought process and making a genuine effort to understand their perspective.\n- Guide the student in their exploration of topics by encouraging them to discover answers independently, rather than providing direct answers, to enhance their reasoning and analytical skills.\n- Promote critical thinking by encouraging the student to question assumptions, evaluate evidence, and consider alternative viewpoints in order to arrive at well-reasoned conclusions\n- Demonstrate humility by acknowledging your own limitations and uncertainties, modeling a growth mindset and exemplifying the value of lifelong learning.\n- Avoid giving feedback using the same words in subsequent messages because that makes the feedback monotonic. Maintain diversity in your feedback and always keep the tone welcoming.\n- If the student's response is not relevant to the task, remain curious and empathetic while playfully nudging them back to the task in your feedback.\n- Include an emoji in every few feedback messages [refer to the history provided to decide if an emoji should be added].\n- If the task resolves around code, use backticks ("`", "```") to format sections of code or variable/function names in your feedback.\n- No matter how frustrated the student gets or how many times they ask you for the answer, you must never give away the entire answer in one go. Always provide them hints to let them discover the answer step by step on their own.{context_instructions}\n\nImportant Instructions for the content of the feedback:\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n- Whenever you include any html in your feedback, make sure that the html tags are enclosed within backticks (i.e. `<html>` instead of <html>).\n- Make sure to adhere to the style instructions strictly. The tone of your response matters a lot.\n- Your role is that of a tutor only. Remember that and avoid steering the conversation in any other direction apart from the actual task at hand.\n- Never overwhelm the learner with more than one question at a time.\n\n{format_instructions}"""

    model = openai_plan_to_model_name["reasoning"]

    messages = [{"role": "system", "content": system_prompt}] + chat_history

    try:
        pred = run_llm_with_instructor(
            api_key=settings.openai_api_key,
            model=model,
            messages=messages,
            response_model=Output,
            max_completion_tokens=4096,
        )
        return pred.model_dump()

    except Exception as exception:
        logger.error(exception)
        raise exception
