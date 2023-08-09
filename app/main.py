import os

from typing import List
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

from gpt import call_openai_chat_model, run_openai_chat_chain, stream_openai_chat_chain
from models import (
    GenerateTrainingQuestionRequest,
    ChatMarkupLanguage,
    TrainingChatRequest,
    TrainingChatResponse,
)
from settings import settings, get_env_file_path

load_dotenv(get_env_file_path())

openai.api_key = settings.openai_api_key
openai.organization = settings.openai_org_id
os.environ["WANDB_API_KEY"] = settings.wandb_api_key

if not os.getenv("ENV"):
    # only run W&B for local
    os.environ["LANGCHAIN_WANDB_TRACING"] = "true"

QUERY_TYPE_ANSWER_KEY = "answer"
QUERY_TYPE_CLARIFICATION_KEY = "clarification"
QUERY_TYPE_IRRELEVANT_KEY = "irrelevant"

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
    # dependencies=[Depends(init_wandb_for_generate_question)],
)
async def generate_training_question(
    question_params: GenerateTrainingQuestionRequest,
) -> str:
    model = "gpt-4-0613"

    system_prompt_template = """
    You are a helpful and encouraging interviewer. 
    You will be specified with a topic, sub-topic, concept, blooms level, and learning outcome that the user needs to be tested on. 
    Ask one question for the specified topic, sub-topic, concept, blooms level and learning outcome.
    Include the answer format you expect from user in the question itself. 
    
    Important:
    - Avoid including any heading or section in your answer
    - Use the appropriate formatting for any part of the question that involves code (e.g. enclosing variables within ``)
    - Do not reveal the answer to the question or include any hints
    """

    user_prompt_template = """
    Topic - {topic}\n
    Sub-Topic - {sub_topic}\n
    Concept - {concept}\n
    Blooms level - {blooms_level}\n
    Learning outcome - {learning_outcome}
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
        sub_topic=question_params.sub_topic,
        concept=question_params.concept,
        blooms_level=question_params.blooms_level,
        learning_outcome=question_params.learning_outcome,
    ).to_messages()

    return StreamingResponse(
        call_openai_chat_model(messages, model=model, max_tokens=1024, streaming=True),
        media_type="text/event-stream",
    )


def run_router_chain(
    user_response: ChatMarkupLanguage, history: List[ChatMarkupLanguage]
):
    system_prompt_template = """You will be provided with a series of interactions between a student and an interviewer along with a student query. 
    The interviewer has asked the student a particular question and the student has responded back with a query. 
    The student query will be delimited with #### characters.
 
    Classify each query into one of the categories below:
    - Answer to the question
    - Clarifying question
    - Irrelevant to the question
    
    Important:
    - If the query does not clearly provide a valid answer to the question asked before, it is not an answer.
    - If the query does not clearly seek clarification based on the conversation before, it is not a clarifying question.
    - If the query is neither an answer nor a clarifying question, it is irrelevant.
    - Give a short explanation before giving the answer.
    
    Provide the answer in the following format:
    Let's think step by step
    {{concise explanation (< 20 words)}}

    {format_instructions}
    """
    output_schema = ResponseSchema(
        name="type",
        description=f"either of '{QUERY_TYPE_ANSWER_KEY}', '{QUERY_TYPE_CLARIFICATION_KEY}', '{QUERY_TYPE_IRRELEVANT_KEY}'",
        type=f"{QUERY_TYPE_ANSWER_KEY} | {QUERY_TYPE_CLARIFICATION_KEY} | {QUERY_TYPE_IRRELEVANT_KEY}",
    )
    output_parser = StructuredOutputParser.from_response_schemas([output_schema])
    format_instructions = output_parser.get_format_instructions()
    system_prompt = system_prompt_template.format(
        format_instructions=format_instructions
    )
    # since this will be interpreted as a format string, we need to escape the curly braces
    system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")

    user_prompt_template_message = "####{input}####"

    response = run_openai_chat_chain(
        user_prompt_template_message,
        user_response.content,
        system_prompt,
        history,
        output_parser,
        model="gpt-3.5-turbo-0613",
        verbose=True,
    )

    if "type" in response:
        return {"success": True, **response}

    return {"success": False}


def run_evaluator_chain(
    user_response: ChatMarkupLanguage, history: List[ChatMarkupLanguage]
):
    system_prompt_template = """You are a helpful and encouraging interviewer.
    You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question that the student needs to be tested on as well as the student's response to the question. 
    You need to provide an evaluation based on the student's response. 
    The student's response will be delimited with #### characters.

    To solve the problem, do the following
    - First, work out your own solution to the problem
    - Then, compare your solution to the student's solution.
    - Assess the student using a rating of 0 (Unsatisfactory), 1 (Satisfactory) or 2 (Proficient).
    - At the end, give some actionable feedback too.
    
    Important:
    - Don’t reveal the answer or give any hints as part of your feedback. 

    Use the following format:
    Actual solution:
    {{concise steps to work out the solution and your solution}}

    {format_instructions}"""

    answer_schema = ResponseSchema(
        name="answer_evaluation",
        description="the final evaluation",
        type="0 | 1 | 2",
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
    # since this will be interpreted as a format string, we need to escape the curly braces
    # first convert any existing double curly braces to single curly braces
    system_prompt = system_prompt.replace("{{", "{").replace("}}", "}")
    # now escape all the curly braces
    system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")

    user_prompt_template_message = "####{input}####"

    response = run_openai_chat_chain(
        user_prompt_template_message,
        user_response.content,
        system_prompt,
        history,
        output_parser,
        ignore_types=[
            QUERY_TYPE_CLARIFICATION_KEY,
            QUERY_TYPE_IRRELEVANT_KEY,
        ],  # during evaluation, don't need to consider past clarifications or irrelevant messages
        verbose=True,
        parse_llm_output_for_key=answer_schema.name,
    )

    if answer_schema.name in response and "feedback" in response:
        return {
            "success": True,
            "feedback": response["feedback"],
            "answer": response[answer_schema.name],
        }

    return {"success": False}


def run_clarifier_chain(
    user_response: ChatMarkupLanguage, history: List[ChatMarkupLanguage]
):
    system_prompt = """You are a helpful and encouraging interviewer.
    You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question that the student needs to be tested on along with a series of interactions between a student and you.

    The student has asked a clarifying question that you need to answer. The student's response will be delimited with #### characters

    Important:
    - Make sure to not give hints or answer the question.
    - If the student asks for the answer, refrain from answering.
    
    The final output should be just a string with the clarification asked for and nothing else.
    """

    user_prompt_template = "####{input}####"

    # response = run_openai_chat_chain(
    #     user_prompt_template,
    #     user_response.content,
    #     system_prompt,
    #     history,
    #     verbose=True,
    # )

    # return {"success": True, "response": response}
    return stream_openai_chat_chain(
        user_prompt_template,
        user_response.content,
        system_prompt,
        history,
        stream_start_tokens=[QUERY_TYPE_CLARIFICATION_KEY],
        verbose=True,
    )


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
    # dependencies=[Depends(init_wandb_for_training_chat)],
)
def training_chat(training_chat_request: TrainingChatRequest):
    # TODO: handle memory

    if not training_chat_request.messages:
        raise HTTPException(status_code=400, detail="messages cannot be empty")

    history = training_chat_request.messages[:-1]
    query = training_chat_request.messages[-1]

    router_response = run_router_chain(user_response=query, history=history)
    if not router_response["success"]:
        raise HTTPException(status_code=500, detail="Something went wrong with router")

    query_type = router_response["type"]

    print(f"Query type: {query_type}")

    if query_type == QUERY_TYPE_ANSWER_KEY:
        evaluator_response = run_evaluator_chain(user_response=query, history=history)
        if evaluator_response["success"]:
            evaluator_response.pop("success")
            return {"type": query_type, "response": evaluator_response}

        raise HTTPException(
            status_code=500, detail="Something went wrong with Evaluator"
        )

    if query_type == QUERY_TYPE_CLARIFICATION_KEY:
        # clarifier_response = run_clarifier_chain(user_response=query, history=history)
        # if clarifier_response["success"]:
        #     clarifier_response.pop("success")
        #     return {"type": query_type, **clarifier_response}

        # raise HTTPException(
        #     status_code=500, detail="Something went wrong with Clarifier"
        # )

        def stream_clarification_response():
            generator = run_clarifier_chain(user_response=query, history=history)
            for value in generator:
                yield value

        return StreamingResponse(
            stream_clarification_response(),
            media_type="text/event-stream",
        )

    def return_query_type():
        yield query_type

    return StreamingResponse(
        return_query_type(),
        media_type="text/event-stream",
    )
