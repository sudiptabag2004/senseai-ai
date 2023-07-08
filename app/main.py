import os

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
import openai
from langchain.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    ChatPromptTemplate,
)
from langchain.output_parsers import (
    ResponseSchema,
    StructuredOutputParser,
)

from langchain.schema import SystemMessage
from dotenv import load_dotenv
import wandb

from gpt import call_openai_chat_model, run_openai_chat_chain
from models import (
    GenerateTrainingQuestionRequest,
    GenerateTrainingQuestionResponse,
    TrainingChatRequest,
    TrainingChatResponse,
)
from settings import settings, get_env_file_path

load_dotenv(get_env_file_path())

openai.api_key = settings.openai_api_key
openai.organization = settings.openai_org_id
os.environ["WANDB_API_KEY"] = settings.wandb_api_key
os.environ["LANGCHAIN_WANDB_TRACING"] = "true"

app = FastAPI()


@app.middleware("http")
async def finish_wandb_process(request: Request, call_next):
    response = await call_next(request)
    wandb.finish(quiet=True)
    return response


def init_wandb_for_generate_question():
    wandb.init(
        project="sensai-ai",
        entity="sensaihv",
        group="training",
        job_type="generate_question",
    )


@app.post(
    "/training/question",
    response_model=GenerateTrainingQuestionResponse,
    dependencies=[Depends(init_wandb_for_generate_question)],
)
def generate_training_question(question_params: GenerateTrainingQuestionRequest):
    print("here")
    model = "gpt-4-0613"

    system_prompt_template = """
    You are a helpful and encouraging interviewer. 
    You will be specified with a topic, a blooms level, and learning outcome that the user needs to be tested on. 
    Ask one question for the specified topic, blooms level and learning outcome.
    Include the answer format you expect from user in the question itself.
    """

    user_prompt_template = """
    Topic: {topic}
    Blooms level: {blooms_level}
    Learning outcome: {learning_outcome}
    """

    system_prompt_template = SystemMessagePromptTemplate.from_template(
        system_prompt_template
    )
    user_prompt_template = HumanMessagePromptTemplate.from_template(
        user_prompt_template
    )
    chat_prompt_template = ChatPromptTemplate.from_messages(
        [system_prompt_template, user_prompt_template]
    )

    messages = chat_prompt_template.format_prompt(
        topic=question_params.topic,
        blooms_level=question_params.blooms_level,
        learning_outcome=question_params.learning_outcome,
    ).to_messages()

    def stream_question():
        for chunk in call_openai_chat_model(
            messages, model=model, max_tokens=1024, streaming=True
        ):
            yield chunk

    return StreamingResponse(stream_question())


def run_router_chain(input, history):
    system_prompt_template = """You will be provided with a series of interactions between a student and an interviewer along with a student query. The interviewer has asked the student a particular question. The student query will be delimited with #### characters.
 
    Classify each query into one of the categories below:
    - Answer to the question
    - Clarifying question
    - Irrelevant to the question

    {format_instructions}
    """
    output_schema = ResponseSchema(
        name="type",
        description="either of 'answer', 'clarification', 'irrelevant'",
        type="answer | clarification | irrelevant",
    )
    output_parser = StructuredOutputParser.from_response_schemas([output_schema])
    format_instructions = output_parser.get_format_instructions()
    system_prompt = system_prompt_template.format(
        format_instructions=format_instructions
    )
    user_prompt_template_message = "####{input}####"
    chain_input = user_prompt_template_message.format(input=input)

    response = run_openai_chat_chain(
        chain_input,
        system_prompt,
        history,
        output_parser,
        verbose=True,
    )

    if "type" in response:
        return {"success": True, **response}

    return {"success": False}


def run_evaluator_chain(input, history):
    system_prompt_template = """You are a helpful and encouraging interviewer.
    You will be specified with a topic, a blooms level, and learning outcome along with a question that the student needs to be tested on as well as the student's response to the question. You need to provide an evaluation based on the student's response. The student's response will be delimited with #### characters.

    To solve the problem, do the following
    - First, work out your own solution to the problem
    - Then, compare your solution to the student's solution. Don’t give any answers or hints. Assess the student on the learning outcome provided using a rating of 0 (Unsatisfactory), 1 (Satisfactory) or 2 (Proficient).
    - At the end, give some actionable feedback too.

    Use the following format:
    Actual solution:
    {{ concise steps to work out the solution and your solution here }}

    {format_instructions}"""

    answer_schema = ResponseSchema(
        name="answer",
        description="the final evaluation",
        type="integer",
    )
    feedback_schema = ResponseSchema(
        name="feedback",
        description="the feedback for the student",
        type="string",
    )
    output_parser = StructuredOutputParser.from_response_schemas(
        [answer_schema, feedback_schema]
    )
    format_instructions = output_parser.get_format_instructions()
    system_prompt = system_prompt_template.format(
        format_instructions=format_instructions
    )
    user_prompt_template_message = "####{input}####"
    chain_input = user_prompt_template_message.format(input=input)

    response = run_openai_chat_chain(
        chain_input,
        system_prompt,
        [
            history[
                0
            ]  # first message should contain detail about topic/question/LO/blooms level
        ],
        output_parser,
        verbose=True,
    )

    if "answer" in response and "feedback" in response:
        return {"success": True, **response}

    return {"success": False}


def run_clarifier_chain(input, history):
    system_prompt = """You are a helpful and encouraging interviewer.
    You will be specified with a topic, a blooms level, and learning outcome along with a question that the student needs to be tested on along with a series of interactions between a student and you.

    The student has asked a clarifying question that you need to answer. The student's response will be delimited with #### characters

    Important:
    - Make sure to not give hints or answer the question.
    - If the student asks for the answer, refrain from answering."""

    user_prompt_template_message = "####{input}####"
    chain_input = user_prompt_template_message.format(input=input)

    response = run_openai_chat_chain(
        chain_input,
        system_prompt,
        history,
        verbose=True,
    )

    return {"success": True, "response": response}


def init_wandb_for_training_chat():
    wandb.init(
        project="sensai-ai",
        entity="sensaihv",
        group="training",
        job_type="chat",
    )


@app.post(
    "/training/chat",
    response_model=TrainingChatResponse,
    dependencies=[Depends(init_wandb_for_training_chat)],
)
def training_chat(training_chat_request: TrainingChatRequest):
    # TODO: handle memory
    # TODO: make sure to handle wandb exception when deploying as well

    if not training_chat_request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    history = training_chat_request.messages[:-1]
    query = training_chat_request.messages[-1]

    router_response = run_router_chain(input=query, history=history)
    if not router_response["success"]:
        raise HTTPException(status_code=500, detail="Something went wrong with router")

    query_type = router_response["type"]

    print(f"Query type: {query_type}")

    if query_type == "answer":
        evaluator_response = run_evaluator_chain(input=query, history=history)
        if evaluator_response["success"]:
            evaluator_response.pop("success")
            return {"type": query_type, "response": evaluator_response}

        raise HTTPException(
            status_code=500, detail="Something went wrong with Evaluator"
        )

    if query_type == "clarification":
        clarifier_response = run_clarifier_chain(input=query, history=history)
        if clarifier_response["success"]:
            clarifier_response.pop("success")
            return {"type": query_type, **clarifier_response}

        raise HTTPException(
            status_code=500, detail="Something went wrong with Clarifier"
        )

    return {"type": query_type}
