import os
from typing import List
from typing_extensions import Annotated

from fastapi import FastAPI, Depends
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

import wandb
from wandb.integration.langchain import WandbTracer

from langchain.schema import SystemMessage
from dotenv import load_dotenv

from gpt import call_openai_chat_model, parse_llm_output
from models import GenerateTrainingQuestionRequest, GenerateTrainingQuestionResponse
from settings import settings, get_env_file_path

load_dotenv(get_env_file_path())

# from sensai import create_learning_outcomes
# client = MongoClient(mongodb_uri)
# db = client["sensai"]
# subjects_collection = db["subjects"]
# users_collection = db["users"]
# assessments_collection = db["assessments"]

openai.api_key = settings.openai_api_key
openai.organization = settings.openai_org_id
os.environ["WANDB_API_KEY"] = settings.wandb_api_key

app = FastAPI()


# @app.get("/")
# def read_root():
#     print(subjects_collection.find_one({"subject": "JavaScript"}))
#     return subjects_collection.find_one({"subject": "JavaScript"})


def get_generate_training_question_callbacks():
    wandb.init(
        project="sensai-ai",
        entity="sensaihv",
        group="training",
        job_type="generate_question",
    )

    wandb_trace_callback = WandbTracer()
    callbacks = [wandb_trace_callback]
    try:
        yield callbacks
    finally:
        WandbTracer.finish()


def get_training_chat_callbacks():
    wandb.init(
        project="sensai-ai",
        entity="sensaihv",
        group="training",
        job_type="chat",
    )

    wandb_trace_callback = WandbTracer()
    callbacks = [wandb_trace_callback]
    try:
        yield callbacks
    finally:
        WandbTracer.finish()


@app.post("/training/question", response_model=GenerateTrainingQuestionResponse)
def generate_training_question(
    callbacks: Annotated[List, Depends(get_generate_training_question_callbacks)],
    question_params: GenerateTrainingQuestionRequest,
):
    model = "gpt-4-0613"

    system_prompt_template = """
    You are a helpful and encouraging interviewer. 
    You will be specified with a topic, a blooms level, and learning outcome that the user needs to be tested on. 
    Ask one question for the specified topic, blooms level and learning outcome.
    Include the answer format you expect from user in the question itself.
    
    {format_instructions}
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

    question_schema = ResponseSchema(
        name="question",
        description="The generated question",
        type="string",
    )

    output_parser = StructuredOutputParser.from_response_schemas([question_schema])
    format_instructions = output_parser.get_format_instructions()

    messages = chat_prompt_template.format_prompt(
        format_instructions=format_instructions,
        topic=question_params.topic,
        blooms_level=question_params.blooms_level,
        learning_outcome=question_params.learning_outcome,
    ).to_messages()

    try:
        response = call_openai_chat_model(
            messages,
            model=model,
            max_tokens=1024,
            callbacks=callbacks,
        )

        response = parse_llm_output(
            output_parser, response, model, default={"question": ""}
        )

        question = response["question"]
        # import ipdb
        # ipdb.set_trace()
        if not question:
            return {"success": False}

        return {"success": True, "question": question}
    except:
        return {"sucess": False}


def training_chat(
    callbacks: Annotated[List, Depends(get_training_chat_callbacks)],
    question_params: GenerateTrainingQuestionRequest,
):
    # TODO: handle memory
    pass
