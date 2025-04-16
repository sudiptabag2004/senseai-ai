from ast import List
import tempfile
from fastapi import APIRouter, HTTPException, File, UploadFile
from fastapi.params import Form
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator, Optional, Dict, Literal
import json
import instructor
import openai
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from api.config import openai_plan_to_model_name
from api.models import (
    TaskAIResponseType,
    AIChatRequest,
    ChatResponseType,
    TaskType,
)
from api.llm import run_llm_with_instructor, stream_llm_with_instructor
from api.settings import settings
from api.utils.logging import logger
from api.db import (
    get_question_chat_history_for_user,
    get_question,
    construct_description_from_blocks,
    fetch_blocks,
    get_task,
    add_generated_course_modules,
    update_course_name,
    create_draft_task_for_course,
)
from api.utils.s3 import download_file_from_s3_as_bytes, get_media_upload_s3_key
from api.utils.audio import prepare_audio_input_for_ai

router = APIRouter()


def get_user_message_for_audio(uuid: str):
    audio_data = download_file_from_s3_as_bytes(get_media_upload_s3_key(uuid, "wav"))

    return [
        {
            "type": "input_audio",
            "input_audio": {
                "data": prepare_audio_input_for_ai(audio_data),
                "format": "wav",
            },
        },
    ]


async def rewrite_query_for_doubt_solving(chat_history: List[Dict]) -> str:
    system_prompt = f"""You are a very good communicator.\n\nYou will receive:\n- A Reference Material\n- Conversation history with a student\n- The student's latest query/message.\n\nYour role: You need to rewrite the student's latest query/message by taking the reference material and the conversation history into consideration so that the query becomes more specific, detailed and clear, reflecting the actual intent of the student."""

    model = openai_plan_to_model_name["text-mini"]

    messages = [{"role": "system", "content": system_prompt}] + chat_history

    class Output(BaseModel):
        rewritten_query: str = Field(
            description="The rewritten query/message of the student"
        )

    pred = await run_llm_with_instructor(
        api_key=settings.openai_api_key,
        model=model,
        messages=messages,
        response_model=Output,
        max_completion_tokens=8192,
    )

    return pred.rewritten_query


def get_ai_message_for_chat_history(ai_message: Dict) -> str:
    message = json.loads(ai_message)

    if "scorecard" not in message or not message["scorecard"]:
        return message["feedback"]

    scorecard_as_prompt = []
    for criterion in message["scorecard"]:
        row_as_prompt = ""
        row_as_prompt += f"""- **{criterion['category']}**\n"""
        if criterion["feedback"].get("correct"):
            row_as_prompt += (
                f"""  What worked well: {criterion['feedback']['correct']}\n"""
            )
        if criterion["feedback"].get("wrong"):
            row_as_prompt += (
                f"""  What needs improvement: {criterion['feedback']['wrong']}\n"""
            )
        row_as_prompt += f"""  Score: {criterion['score']}"""
        scorecard_as_prompt.append(row_as_prompt)

    scorecard_as_prompt = "\n".join(scorecard_as_prompt)
    return f"""Feedback:\n```\n{message['feedback']}\n```\n\nScorecard:\n```\n{scorecard_as_prompt}\n```"""


@router.post("/chat")
async def ai_response_for_question(request: AIChatRequest):
    if request.task_type in [TaskType.EXAM, TaskType.QUIZ]:
        if request.question_id is None and request.question is None:
            raise HTTPException(
                status_code=400,
                detail=f"Question ID or question is required for {request.task_type} tasks",
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
    else:
        if request.task_id is None:
            raise HTTPException(
                status_code=400,
                detail="Task ID is required for learning material tasks",
            )

        if request.chat_history is None:
            raise HTTPException(
                status_code=400,
                detail="Chat history is required for learning material tasks",
            )

    if request.task_type == TaskType.LEARNING_MATERIAL:
        task = await get_task(request.task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        chat_history = request.chat_history

        reference_material = construct_description_from_blocks(task["blocks"])
        question_details = f"""Reference Material:\n```\n{reference_material}\n```"""
    else:
        if request.question_id:
            question = await get_question(request.question_id)
            if not question:
                raise HTTPException(status_code=404, detail="Question not found")

            chat_history = await get_question_chat_history_for_user(
                request.question_id, request.user_id
            )
            chat_history = [
                {"role": message["role"], "content": message["content"]}
                for message in chat_history
            ]
        else:
            question = request.question.model_dump()
            chat_history = request.chat_history

        question_description = construct_description_from_blocks(question["blocks"])
        question_details = f"""Task:\n```\n{question_description}\n```"""

        for message in chat_history:
            if message["role"] != "user":
                message["content"] = get_ai_message_for_chat_history(message["content"])

    if request.response_type == ChatResponseType.AUDIO:
        for message in chat_history:
            if message["role"] != "user":
                continue

            message["content"] = get_user_message_for_audio(message["content"])

    user_message = (
        get_user_message_for_audio(request.user_response)
        if request.response_type == ChatResponseType.AUDIO
        else request.user_response
    )

    user_message = {"role": "user", "content": user_message}

    if request.task_type in [TaskType.EXAM, TaskType.QUIZ]:
        if question["response_type"] in [TaskAIResponseType.CHAT]:
            answer_as_prompt = construct_description_from_blocks(question["answer"])
            question_details += f"""\n\nReference Solution (never to be shared with the learner):\n```\n{answer_as_prompt}\n```"""
        else:
            scoring_criteria_as_prompt = ""
            for criterion in question["scorecard"]["criteria"]:
                scoring_criteria_as_prompt += f"""- **{criterion['name']}** [min: {criterion['min_score']}, max: {criterion['max_score']}]: {criterion['description']}\n"""

            question_details += (
                f"""\n\nScoring Criteria:\n```\n{scoring_criteria_as_prompt}\n```"""
            )

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

    if request.task_type in [TaskType.EXAM, TaskType.QUIZ]:
        if question["response_type"] == TaskAIResponseType.CHAT:

            class Output(BaseModel):
                feedback: str = Field(
                    description="Feedback on the student's response; add newline characters to the feedback to make it more readable where necessary"
                )
                is_correct: bool = Field(
                    description="Whether the student's response correctly solves the task that the student is supposed to solve. For this to be true, the task needs to be completely solved and not just partially solved."
                )

        else:

            class Feedback(BaseModel):
                correct: Optional[str] = Field(description="What worked well")
                wrong: Optional[str] = Field(description="What needs improvement")

            class Row(BaseModel):
                category: str = Field(
                    description="Category from the scoring criteria for which the feedback is being provided"
                )
                feedback: Feedback = Field(
                    description="Detailed feedback for this category"
                )
                score: int = Field(
                    description="Score given within the min/max range for this category"
                )
                max_score: int = Field(description="Maximum score for this category")

            class Output(BaseModel):
                feedback: str = Field(
                    description="A single, comprehensive summary based on the scoring criteria"
                )
                scorecard: Optional[List[Row]] = Field(
                    description="List of rows with one row for each category from scoring criteria; only include this in the response if the student's response is an answer to the task"
                )

    else:

        class Output(BaseModel):
            response: str = Field(
                description="Response to the student's query; add proper formatting to the response to make it more readable where necessary"
            )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    if request.task_type in [TaskType.EXAM, TaskType.QUIZ]:
        knowledge_base = None

        if question["context"]:
            linked_learning_material_ids = question["context"]["linkedMaterialIds"]
            knowledge_blocks = question["context"]["blocks"]

            if linked_learning_material_ids:
                for id in linked_learning_material_ids:
                    blocks = await fetch_blocks(int(id), "task")
                    knowledge_blocks += blocks

            knowledge_base = construct_description_from_blocks(knowledge_blocks)

        context_instructions = ""
        if knowledge_base:
            context_instructions = f"""\n\nMake sure to use only the information provided within ``` below for responding to the student while ignoring any other information that contradicts the information provided:\n\n```\n{knowledge_base}\n```"""

        if question["response_type"] in [TaskAIResponseType.CHAT]:
            system_prompt = f"""You are a Socratic tutor.\n\nYou will receive:\n- Task description\n- Task solution (for your reference only; do not reveal)\n- Conversation history with the student{context_instructions}\n\nYour role:\n- Engage students with open-ended questions to encourage deep reflection and critical thinking.\n- Foster a respectful, welcoming dialogue; value diverse viewpoints.\n- Listen actively, paying attention to the student's reasoning and thought process.\n- Encourage students to independently discover answers; you can never ever provide direct answers or explanations.\n- Prompt students to question assumptions, assess evidence, and explore alternative perspectives.\n- Maintain humility, acknowledge uncertainties, and model lifelong learning.\n- Never provide complete solutions outright, regardless of student frustration; guide them step-by-step.\n- The student does not have access to the solution. The solution has only been given to you for evaluating the student's response. Keep this in mind while responding to the student.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n\nGuidelines on your feedback style:\n- Vary your phrasing to avoid monotony; occasionally include emojis to maintain warmth and engagement.\n- Playfully redirect irrelevant responses back to the task without judgment.\n- If the task involves code, format code snippets or variable/function names with backticks (`example`).\n- If including HTML, wrap tags in backticks (`<html>`).\n- If your response includes rich text format like lists, font weights, tables, etc. always render them as markdown.\n- Ask only one reflective question per response otherwise the student will get overwhelmed.\n- Avoid being unnecessarily verbose in your feedback.\n\nGuidelines on assessing correctness of the student's answer:\n- Once the student has provided an answer that is correct with respect to the solution provided at the start, clearly acknowledge that they have got the correct answer and stop asking any more reflective questions. Your response should make them feel a sense of completion and accomplishment at a job well done.\n- If the question is a subjective type question where the answer does not need to match word-for-word with the solution, only assess whether the student's answer covers the entire essence of the correct solution.\n- Avoid bringing in your judgement of what the right answer should be. What matters for evaluation is the solution provided to you and the response of the student. Keep your biases outside. Be objective in comparing these two. As soon as the student gets the answer correct, stop asking any further reflective questions.\n- The student might get the answer right without any probing required from your side in the first couple of attempts itself. In that case, remember the instruction provided above to acknowledge their answer's correctness and to stop asking further questions.\n\nGuideline on maintaining focus:\n- Your role is that of a tutor for this particular task only. Remember that and absolutely avoid steering the conversation in any other direction apart from the actual task give to you.\n- If the student tries to move the focus of the conversation away from the task, gently bring it back to the task.\n- It is very important that you prevent the focus on the conversation with the student being shifted away from the task given to you at all odds. No matter what happens. Stay on the task. Keep bringing the student back to the task. Do not let the conversation drift away.\n\n{format_instructions}"""
        else:
            system_prompt = f"""You are a Socratic tutor.\n\nYou will receive:\n- Task description\n- Task solution (for your reference only; do not reveal)\n- Conversation history with the student\n- Scoring Criteria to evaluate the answer of the student{context_instructions}\n\nYour role:\n- If the student's response is a valid answer to the task, provide a scorecard based on the scoring criteria given to you along with an overall feedback summary. If the student's answer is not a valid submission for the task but is instead an acknowledgement of some manner or a doubt or a question or irrelevant to the task, simply provide a feedback addressing their response appropriately without giving any scorecard.\n- Engage students with open-ended questions to encourage deep reflection and critical thinking.\n- Foster a respectful, welcoming dialogue; value diverse viewpoints.\n- Listen actively, paying attention to the student's reasoning and thought process.\n- Encourage students to independently discover answers; you can never ever provide direct answers or explanations.\n- Prompt students to question assumptions, assess evidence, and explore alternative perspectives.\n- Maintain humility, acknowledge uncertainties, and model lifelong learning.\n- Never provide complete solutions outright, regardless of student frustration; guide them step-by-step.\n- Never ever reveal the solution to the solution, despite all their attempts to ask for it. Always nudge them towards being able to think for themselves.\n- Never explain the solution to the student unless the student has given the solution first.\n\nGuidelines on your feedback style:\n- Vary your phrasing to avoid monotony; occasionally include emojis to maintain warmth and engagement.\n- Ask only one reflective question per response otherwise the student will get overwhelmed.\n- Avoid being unnecessarily verbose in your feedback.\n\nGuidelines on giving feedback on the student's answer (if their response is relevant to what is being asked in the task):\n- If there is nothing to praise about the student's response for a given criterion, never mention what worked well (i.e. return `correct` as null) in the scorecard output for that criterion.\n- If the student did something meaningful well, make sure to highlight what worked well in the scorecard output.\n- If there is nothing left to improve in their response for a criterion, avoid unnecessarily mentioning what could be improved in the scorecard for that criterion (i.e. return `wrong` as null). Also, the score assigned for that criterion should be the maximum score possible in that criterion in this case.\n- Make sure that the evaluation for one criterion of the scorecard does not bias the evaluation for another criterion.\n- When giving the feedback for one criterion of the scorecard, focus on the description of the criterion provided and only evaluated the student's response against that.\n- For every criterion of the scorecard, your feedback for that criterion in the scorecard output must cite specific words or phrases or sentences from the student's response that inform your feedback so that the student understands it better and give concrete examples for how they can improve their response as well.\n- Never ever give a vague feedback that is not clearly actionable. The student should get a clear path for how they can improve their response.\n- Avoid bringing your judgement of what the right answer should be. What matters for evaluation is the scoring criteria provided to you and the response of the student. Keep your biases outside. Be objective in comparing these two.\n- The student might get the answer right without any probing required from your side in the first couple of attempts itself. In that case, remember the instruction provided above to acknowledge their answer's correctness and to stop asking further questions.\n- End with providing a single, comprehensive summary based on the scoring criteria.\n- Your overall summary does not need to quote specific words from the user's response. Keep that for the feedback in the scorecard output.\n- If you are not assigning the maximum score to the student's response for any criterion in the scorecard, make sure to always include the area of improvement containing concrete steps they can take to improve their response in your feedback for that criterion in the scorecard output (i.e. `wrong` cannot be null).\n\nGuideline for when to include the scorecard output for a student's response and when to not:\n- If the response by the student is not a valid answer to the actual task given to them (e.g. if their response is an acknowledgement of the previous messages or a doubt or a question or something irrelevant to the task), do not provide any scorecard in that case and only return a feedback addressing their response.\n- For messages of acknowledgement, you do not need to explicitly call it out as an acknowledgement. Simply respond to it normally.\n\nGuideline on maintaining focus on the task you are responsible for:\n- Your role is that of a tutor for this particular task only. Remember that and absolutely avoid steering the conversation in any other direction apart from the actual task give to you.\n- If the student tries to move the focus of the conversation away from the task, gently bring it back to the task.\n- It is very important that you prevent the focus on the conversation with the student being shifted away from the task given to you at all odds. No matter what happens. Stay on the task. Keep bringing the student back to the task. Do not let the conversation drift away.\n\n{format_instructions}"""
    else:
        system_prompt = f"""You are a teaching assistant.\n\nYou will receive:\n- A Reference Material\n- Conversation history with a student\n- The student's latest query/message.\n\nYour role:\n- You need to respond to the student's message based on the content in the reference material provided to you.\n- If the student's query is absolutely not relevant to the reference material or goes beyond the scope of the reference material, clearly saying so without indulging their irrelevant queries. The only exception is when they are asking deeper questions related to the learning material that might not be mentioned in the reference material itself to clarify their conceptual doubts. In this case, you can provide the answer and help them.\n- Remember that the reference material is in read-only mode for the student. So, they cannot make any changes to it.\n\nGuidelines on your response style:\n- Vary your phrasing to avoid monotony; occasionally include emojis to maintain warmth and engagement.\n- Playfully redirect irrelevant responses back to the task without judgment.\n- If the task involves code, format code snippets or variable/function names with backticks (`example`).\n- If including HTML, wrap tags in backticks (`<html>`).\n- If your response includes rich text format like lists, font weights, tables, etc. always render them as markdown.\n- Avoid being unnecessarily verbose in your response.\n\nGuideline on maintaining focus:\n- Your role is that of a teaching assistant for this particular task only. Remember that and absolutely avoid steering the conversation in any other direction apart from the actual task give to you.\n- If the student tries to move the focus of the conversation away from the task, gently bring it back to the task.\n- It is very important that you prevent the focus on the conversation with the student being shifted away from the task given to you at all odds. No matter what happens. Stay on the task. Keep bringing the student back to the task. Do not let the conversation drift away.\n\n{format_instructions}"""

        chat_history[-1]["content"] = await rewrite_query_for_doubt_solving(
            chat_history
        )

    if request.response_type == ChatResponseType.AUDIO:
        model = openai_plan_to_model_name["audio"]
    else:
        model = openai_plan_to_model_name["text"]

    messages = [{"role": "system", "content": system_prompt}] + chat_history

    try:
        # Define an async generator for streaming
        async def stream_response() -> AsyncGenerator[str, None]:
            stream = await stream_llm_with_instructor(
                api_key=settings.openai_api_key,
                model=model,
                messages=messages,
                response_model=Output,
                max_completion_tokens=4096,
            )

            # Process the async generator
            async for chunk in stream:
                yield json.dumps(chunk.model_dump()) + "\n"

        # Return a streaming response
        return StreamingResponse(
            stream_response(),
            media_type="application/x-ndjson",
        )

    except Exception as exception:
        logger.error(exception)
        raise exception


async def migrate_content_to_blocks(content: str) -> List[Dict]:
    class BlockProps(BaseModel):
        level: Optional[Literal[1, 2, 3]] = Field(
            description="The level of a heading block"
        )
        checked: Optional[bool] = Field(
            description="Whether the block is checked (for a checkListItem block)"
        )
        language: Optional[str] = Field(
            description="The language of the code block (for a codeBlock block); always the full name of the language in lowercase (e.g. python, javascript, sql, html, css, etc.)"
        )
        name: Optional[str] = Field(
            description="The name of the image (for an image block)"
        )
        url: Optional[str] = Field(
            description="The URL of the image (for an image block)"
        )

    class BlockContentStyle(BaseModel):
        bold: Optional[bool] = Field(description="Whether the text is bold")
        italic: Optional[bool] = Field(description="Whether the text is italic")
        underline: Optional[bool] = Field(description="Whether the text is underlined")

    class BlockContentText(BaseModel):
        type: Literal["text"] = Field(description="The type of the block content")
        text: str = Field(
            description="The text of the block; if the block is a code block, this should contain the code with newlines and tabs as appropriate"
        )
        styles: BlockContentStyle | dict = Field(
            default={}, description="The styles of the block content"
        )

    class BlockContentLink(BaseModel):
        type: Literal["link"] = Field(description="The type of the block content")
        href: str = Field(description="The URL of the link")
        content: List[BlockContentText] = Field(description="The content of the link")

    class Block(BaseModel):
        type: Literal[
            "heading",
            "paragraph",
            "bulletListItem",
            "numberedListItem",
            "codeBlock",
            "checkListItem",
            "image",
        ] = Field(description="The type of block")
        props: Optional[BlockProps | dict] = Field(
            default={}, description="The properties of the block"
        )
        content: List[BlockContentText | BlockContentLink] = Field(
            description="The content of the block; empty for image blocks"
        )

    class Output(BaseModel):
        blocks: List[Block] = Field(description="The blocks of the content")

    system_prompt = f"""You are an expert course converter. The user will give you a content in markdown format. You will need to convert the content into a structured format as given below.

Never modify the actual content given to you. Just convert it into the structured format.

The `content` field of each block should have multiple blocks only when parts of the same line in the markdown content have different parameters or styles (e.g. some part of the line is bold and some is italic or some part of the line is a link and some is not).

The final output should be a JSON in the following format:

{Output.model_json_schema()}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    output = await run_llm_with_instructor(
        api_key=settings.openai_api_key,
        model=openai_plan_to_model_name["text-mini"],
        messages=messages,
        response_model=Output,
        max_completion_tokens=16000,
    )

    blocks = output.model_dump(exclude_none=True)["blocks"]

    for block in blocks:
        if block["type"] == "image":
            block["props"].update(
                {"showPreview": True, "caption": "", "previewWidth": 512}
            )

    return blocks


@router.post("/generate/course/{course_id}/structure")
async def generate_course_structure(
    course_id: int,
    course_description: str = Form(...),
    intended_audience: str = Form(...),
    instructions: Optional[str] = Form(None),
    reference_material: UploadFile = File(...),
):
    openai_client = openai.OpenAI(
        api_key=settings.openai_api_key,
    )

    file = openai_client.files.create(
        file=reference_material.file,
        purpose="user_data",
    )

    class Task(BaseModel):
        name: str = Field(description="The name of the task")
        description: str = Field(
            description="a detailed description of what should the content of that task be"
        )
        type: Literal[TaskType.LEARNING_MATERIAL, TaskType.QUIZ] = Field(
            description="The type of task"
        )

    class Concept(BaseModel):
        name: str = Field(description="The name of the concept")
        description: str = Field(
            description="The description for what the concept is about"
        )
        tasks: List[Task] = Field(description="A list of tasks for the concept")

    class Module(BaseModel):
        name: str = Field(description="The name of the module")
        concepts: List[Concept] = Field(description="A list of concepts for the module")

    class Output(BaseModel):
        name: str = Field(description="The name of the course")
        modules: List[Module] = Field(description="A list of modules for the course")

    system_prompt = f"""You are an expert course creator. The user will give you some instructions for creating a course along with the reference material to be used as the source for the course content.

You need to thoroughly analyse the reference material given to you and come up with a structure for the course. Each course should be structured into modules where each modules represents a full topic.

With each modules, there must be a mix of learning materials and quizzes. A learning material is used for learning about a specific concept in the topic. Keep separate learning materials for different concepts in the same topic/module. For each concept, the learning material for that concept should be followed by one or more quizzes. Each quiz contains multiple questions for testing the understanding of the learner on the actual concept.

Quizzes are where learners can practice a concept. While testing theoretical understanding is important, quizzes should go beyond that and produce practical challenges for the students to apply what they have learnt. If the reference material already has examples/sample problems, include them in the quizzes for the students to practice. If no examples are present in the reference material, generate a few relevant problem statements to test the real-world understanding of each concept for the students.

All explanations should be present in the learning materials and all practice should be done in quizzes. Maintain this separation of purpose for each task type.

No need to come up with the questions inside the quizzes for now. Just focus on producing the right structure.
Don't keep any concept too big. Break a topic down into multiple smaller, ideally independent, concepts. For each concept, follow the sequence of learning material -> quiz before moving to the next concept in that topic.
End the course with a conclusion module (with the appropriate name for the module suited to the course) which ties everything taught in the course together and ideally ends with a capstone project where the learner has to apply everything they have learnt in the course.

Make sure to never skip a single concept from the reference material provided.

The final output should be a JSON in the following format:

{Output.model_json_schema()}

Keep the sequences of modules, concepts, and tasks in mind.

Do not include the type of task in the name of the task."""

    client = instructor.from_openai(openai_client)

    course_structure_generation_prompt = f"""About the course: {course_description}\n\nIntended audience: {intended_audience}"""

    if instructions:
        course_structure_generation_prompt += f"\n\nInstructions: {instructions}"

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "file",
                    "file": {
                        "file_id": file.id,
                    },
                },
            ],
        },
        # separate into 2 user messages for prompt caching to work
        {"role": "user", "content": course_structure_generation_prompt},
    ]

    # TODO: Store file in DB/S3?
    # TODO: store course generation request in DB

    response = client.chat.completions.create(
        model=openai_plan_to_model_name["text"],
        messages=messages,
        response_model=Output,
        max_completion_tokens=16000,
        store=True,
    )

    output = response.model_dump()

    await update_course_name(course_id, output["name"])

    module_ids = await add_generated_course_modules(course_id, output["modules"])

    for index, module in enumerate(output["modules"]):
        for concept in module["concepts"]:
            for task in concept["tasks"]:
                await create_draft_task_for_course(
                    task["name"],
                    task["type"],
                    course_id,
                    module_ids[index],
                )

    return {"success": True}
