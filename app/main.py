import os
from itertools import chain
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
    GenerateEnglishPassageRequest,
    GenerateEnglishQuestionRequest,
    OpenAIChatRole,
    ChatMessageType,
)
from settings import settings, get_env_file_path

load_dotenv(get_env_file_path())

openai.api_key = settings.openai_api_key
openai.organization = settings.openai_org_id
os.environ["WANDB_API_KEY"] = settings.wandb_api_key

# if not os.getenv("ENV"):
#     # only run W&B for local
#     os.environ["LANGCHAIN_WANDB_TRACING"] = "true"

QUERY_TYPE_ANSWER_KEY = "answer"
QUERY_TYPE_CLARIFICATION_KEY = "clarification"
QUERY_TYPE_IRRELEVANT_KEY = "irrelevant"
QUERY_TYPE_MISC_KEY = "miscellaneous"

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
        call_openai_chat_model(
            messages, model=model, max_tokens=1024, streaming=True, cache=True
        ),
        media_type="text/event-stream",
    )


def run_router_chain(
    user_response: ChatMarkupLanguage, history: List[ChatMarkupLanguage]
):
    system_prompt_template = """You will be provided with a series of interactions between a student and an interviewer along with a student query. 
    The interviewer has asked the student a particular question and the student has responded back with a query. 
    The student query will be delimited with #### characters.
 
    Classify each query into one of the categories below:
    - answer
    - clarification
    - irrelevant
    - miscellanous
    
    Important:
    - If the query does not clearly provide a valid answer to the question asked before, it is not an answer.
    - If the query does not clearly seek clarification based on the conversation before, it is not a clarifying question.
    - If the query does not provide an answer or seek clarification but is a response to the question, it is a miscellaneous response. Example: 'not interested', 'okay'.
    - If the query is not related to the question in any way, it is irrelevant.

    {format_instructions}
    """
    output_schema = ResponseSchema(
        name="type",
        description="type of the query",
        type=f"{QUERY_TYPE_ANSWER_KEY} | {QUERY_TYPE_CLARIFICATION_KEY} | {QUERY_TYPE_IRRELEVANT_KEY} | {QUERY_TYPE_MISC_KEY}",
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
        # model="gpt-3.5-turbo-0613",
        verbose=True,
    )

    if "type" in response:
        return {"success": True, **response}

    return {"success": False}


def run_evaluator_chain(
    user_response: ChatMarkupLanguage,
    history: List[ChatMarkupLanguage],
    setup: str = None,
    is_solution_provided: bool = False,
):
    if not is_solution_provided:
        actual_solution_system_prompt_template_message = """You are a helpful and encouraging interviewer.
        You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question.
        You need to work out your own solution to the problem.
        
        Use the following format:
        Actual solution:
        {{concise steps to work out the solution and your solution}}
        """
        actual_solution_user_prompt_template_message = """{input}"""

        actual_solution_system_prompt_template = (
            SystemMessagePromptTemplate.from_template(
                actual_solution_system_prompt_template_message
            )
        )
        actual_solution_user_prompt_template = HumanMessagePromptTemplate.from_template(
            actual_solution_user_prompt_template_message
        )
        actual_solution_chat_prompt_template = ChatPromptTemplate.from_messages(
            [
                actual_solution_system_prompt_template,
                actual_solution_user_prompt_template,
            ]
        )

        # first message should contain the details required
        actual_solution_messages = actual_solution_chat_prompt_template.format_prompt(
            input=history[0].content,
        ).to_messages()

        import time

        start_time = time.time()

        actual_solution_response = call_openai_chat_model(
            actual_solution_messages, model="gpt-4-0613", max_tokens=1024, cache=True
        )

        print(f"Time taken: {time.time() - start_time}")

        # add the actual solution to the history
        history[0].content += f"\n{actual_solution_response}"

    # import ipdb

    # ipdb.set_trace()

    system_prompt_template = """You are a very helpful, accurate, detail-oriented and encouraging interviewer who follows the steps it has been given.
    {setup}
    You need to provide an evaluation based on the student's response. 
    The student's response that you need to evaluate will be delimited with #### characters.

    To solve the problem, follow the steps below:
    - Compare your solution to the student's solution.
    - Assess the student using a rating of 0 (Unsatisfactory), 1 (Satisfactory) or 2 (Proficient).
    - At the end, give some actionable feedback without giving away any part of the answer to the question.
    - End the feedback by nudging the student to try again now.
    
    Important Instructions:
    - The feedback should enable the student to think on their own.
    - You are not required to fix the student's answer. You only need to nudge them in the right direction of thinking.
    - No part of the feedback should contain any part of the answer.
    - If the student made a mistake in the past but corrected it in their latest response, consider the mistake fixed.
    
    Provide the answer in the following format:
    Let's think step by step
    {{concise explanation}}
    
    {format_instructions}"""

    reflection_schema = ResponseSchema(
        name="reflection",
        description="a brief reflection on the student's response in broken englishq to keep it short",
        type="string",
    )
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
        [reflection_schema, answer_schema, feedback_schema]
    )
    format_instructions = output_parser.get_format_instructions()

    if not setup:
        setup = """You will be given a topic, sub-topic, concept, a blooms level, learning outcome, a question that the student needs to be tested on, your actual solution and a series of interactions between the student and you."""

    system_prompt = system_prompt_template.format(
        format_instructions=format_instructions, setup=setup
    )
    # since this will be interpreted as a format string, we need to escape the curly braces
    # first convert any existing double curly braces to single curly braces
    system_prompt = system_prompt.replace("{{", "{").replace("}}", "}")
    # now escape all the curly braces
    system_prompt = system_prompt.replace("{", "{{").replace("}", "}}")

    user_prompt_template_message = "####{input}####"

    # response = run_openai_chat_chain(
    #     user_prompt_template_message,
    #     user_response.content,
    #     system_prompt,
    #     history,
    #     output_parser,
    #     ignore_types=[
    #         QUERY_TYPE_CLARIFICATION_KEY,
    #         QUERY_TYPE_IRRELEVANT_KEY,
    #     ],  # during evaluation, don't need to consider past clarifications or irrelevant messages
    #     verbose=True,
    #     parse_llm_output_for_key=answer_schema.name,
    # )

    # return {
    #     "feedback": response["feedback"],
    #     "answer": response[answer_schema.name],
    # }
    return stream_openai_chat_chain(
        user_prompt_template_message,
        user_response.content,
        system_prompt,
        history,
        ignore_types=[
            QUERY_TYPE_CLARIFICATION_KEY,
            QUERY_TYPE_IRRELEVANT_KEY,
        ],  # during evaluation, don't need to consider past clarifications or irrelevant messages
        verbose=True,
    )


def run_clarifier_chain(
    user_response: ChatMarkupLanguage,
    history: List[ChatMarkupLanguage],
    setup: str = None,
):
    system_prompt_template = """You are a helpful and encouraging interviewer.
    {setup}
    
    The student has asked a clarifying question that you need to answer. The student's response will be delimited with #### characters

    Important:
    - Refrain from answering the question or giving any hints.
    - Giving away the answer to the question would be a sin.

    The final output should be just a string with the clarification asked for, without giving away the answer to the question, and nothing else.
    """
    if not setup:
        setup = """You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question that the student needs to be tested on along with a series of interactions between a student and you."""

    system_prompt = system_prompt_template.format(setup=setup)

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
        verbose=True,
    )


def run_miscellaneous_chain(
    user_response: ChatMarkupLanguage,
    history: List[ChatMarkupLanguage],
    setup: str = None,
):
    system_prompt_template = """You are a helpful and encouraging interviewer.
    {setup}
    
    The student has responded to feedback that you have provided. The student's response will be delimited with #### characters.
    
    Important:
    - Refrain from answering the question or giving any hints.
    - Giving away the answer to the question would be a sin.
    
    The final output should be a reply to the student's response, without giving away the answer to the question, ending on a short encouraging message to try again and nothing else.
    """
    user_prompt_template = "####{input}####"

    if not setup:
        setup = """You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question that the student needs to be tested on along with a series of interactions between a student and you."""

    system_prompt = system_prompt_template.format(setup=setup)

    return stream_openai_chat_chain(
        user_prompt_template,
        user_response.content,
        system_prompt,
        history,
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
async def training_chat(training_chat_request: TrainingChatRequest):
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
        # evaluator_response = run_evaluator_chain(user_response=query, history=history)

        async def get_answer_response():
            yield QUERY_TYPE_ANSWER_KEY

            async for item in run_evaluator_chain(
                user_response=query,
                history=history,
                setup=training_chat_request.evaluator_setup,
                is_solution_provided=training_chat_request.is_solution_provided,
            ):
                yield item

        async def stream_answer_response():
            async for item in get_answer_response():
                yield item

        return StreamingResponse(
            stream_answer_response(),
            media_type="text/event-stream",
        )

    if query_type == QUERY_TYPE_CLARIFICATION_KEY:

        async def get_clarification_response():
            yield QUERY_TYPE_CLARIFICATION_KEY

            async for item in run_clarifier_chain(
                user_response=query,
                history=history,
                setup=training_chat_request.general_setup,
            ):
                yield item

        async def stream_clarification_response():
            async for item in get_clarification_response():
                yield item

        return StreamingResponse(
            stream_clarification_response(),
            media_type="text/event-stream",
        )

    if query_type == QUERY_TYPE_MISC_KEY:

        async def get_miscellaneous_response():
            yield QUERY_TYPE_MISC_KEY

            async for item in run_miscellaneous_chain(
                user_response=query,
                history=history,
                setup=training_chat_request.general_setup,
            ):
                yield item

        async def stream_miscellaneous_response():
            async for item in get_miscellaneous_response():
                yield item

        return StreamingResponse(
            stream_miscellaneous_response(),
            media_type="text/event-stream",
        )

    def return_query_type():
        yield query_type

    return StreamingResponse(
        return_query_type(),
        media_type="text/event-stream",
    )


@app.post(
    "/english/passage",
    # dependencies=[Depends(init_wandb_for_generate_question)],
)
async def generate_english_passage(
    passage_params: GenerateEnglishPassageRequest,
):
    # model = "gpt-4-0613"
    system_prompt_template = """
    You are a helpful and encouraging English language trainer.

    You are interacting with a student for whom English is not the first language, helping them assess their competence in English and nudging them in the right direction. The aim is to help students feel comfortable with the English language. 

    You will be given a difficulty level, a theme and an activity type delimited by ``` characters.
    Your aim is to understand the student better and generate a personalized and engaging passage based on the input. 

    Here the steps you need to follow:
    - Ask the student a maximum of 2-3 questions around the theme to identify a specific interest that they might have
    - Based on the theme and their interest that you've identified, generate a generalized passage
    - Let the passage generated only have a maximum of 2 paragraphs

    Important Instructions:
    - You must contextualize the passage to India
    - Do not reveal the answer to the question or include any hints
    - Maintain a similar format across all the themes
    - Avoid describing the steps that you are going to follow to the students
    - You need to use simple words for the passage
    - Maintain the Foundational level found in the Indian education system throughout the passage
    - Either ask a question to elicit their interest or generate a passage. No explanations needed
    - Avoid asking all the questions simultaneously. Ask one by one
    
    {format_instructions}
    """
    type_schema = ResponseSchema(
        name="type",
        description="whether the response by AI is a question to elicit interest or the generated passage",
        type="passage | interest",
    )
    value_schema = ResponseSchema(
        name="value",
        description="question or the generated passage",
        type="string",
    )
    output_parser = StructuredOutputParser.from_response_schemas(
        [type_schema, value_schema]
    )
    format_instructions = output_parser.get_format_instructions()

    # system_prompt = system_prompt_template.format(
    #     format_instructions=format_instructions
    # )

    user_prompt_template = """{input}"""

    passage_settings = f"""```Difficulty Level - {passage_params.difficulty_level}\nTheme - {passage_params.theme}\nActivity Type - {passage_params.activity_type}```"""

    if not passage_params.messages:
        user_message = passage_settings
        history = []
    else:
        user_message = passage_params.messages[-1].content
        history = [
            ChatMarkupLanguage(role="user", content=passage_settings)
        ] + passage_params.messages[:-1]

    # system_prompt_template = SystemMessagePromptTemplate.from_template(
    #     system_prompt_template
    # )
    # user_prompt_template = HumanMessagePromptTemplate.from_template(
    #     user_prompt_template
    # )
    # chat_prompt_template = ChatPromptTemplate.from_messages(
    #     [system_prompt_template, user_prompt_template]
    # )

    # messages = chat_prompt_template.format_prompt(
    #     theme=passage_params.theme,
    #     difficulty_level=passage_params.difficulty_level,
    #     activity_type=passage_params.activity_type,
    # ).to_messages()

    # return StreamingResponse(
    #     call_openai_chat_model(
    #         messages, model=model, max_tokens=1024, streaming=True, cache=True
    #     ),
    #     media_type="text/event-stream",
    # )
    # user_prompt_template = "####{input}####"
    # user_message = "what format do you need it then?"
    # system_prompt_template = "You are a helpful and encouraging interviewer.\n    You will be specified with a topic, sub-topic, concept, a blooms level, and learning outcome along with a question that the student needs to be tested on along with a series of interactions between a student and you.\n    \n    The student has asked a clarifying question that you need to answer. The student's response will be delimited with #### characters\n\n    Important:\n    - Refrain from answering the question or giving any hints.\n    - Giving away the answer to the question would be a sin.\n\n    The final output should be just a string with the clarification asked for, without giving away the answer to the question, and nothing else.\n    "
    # return

    async def stream_response():
        async for item in stream_openai_chat_chain(
            user_prompt_template,
            user_message,
            system_prompt_template,
            history,
            ignore_types=[],
            verbose=True,
            system_prompt_kwargs={"format_instructions": format_instructions},
        ):
            yield item

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
    )


@app.post(
    "/english/question",
    # dependencies=[Depends(init_wandb_for_generate_question)],
)
async def generate_training_question(
    english_question_params: GenerateEnglishQuestionRequest,
) -> str:
    model = "gpt-4-0613"

    system_prompt_template = """
    You are a helpful and encouraging English language trainer.

    You are interacting with a student for whom English is not the first language, helping them assess their competence in English and nudging them in the right direction. The aim is to help students feel comfortable with the English language.

    You will be given a theme, a difficulty level and a passage. 

    You need to generate questions on the passage to check the student's comprehension. 

    For difficulty level “Beginner”, generate questions of the following types:
    1) Meaning of a difficult word in the passage.
    2) Use a vocabulary word from the passage in a sentence of their own. 
    3) A question where there are multiple options with one correct answer. 

    For difficulty level “Intermediate”, generate questions of the following types:
    1) A question which they can answer in 2-3 sentences.
    2) A question which can connect the passage to them.  

    Important Instructions:
    - Include the answer format you expect from user in the question itself. 
    - Do not reveal the answer to the question or include any hints
    - Maintain the Foundational level found in the Indian education system for the question.
    
    {format_instructions}
    """

    questions_schema = ResponseSchema(
        name="questions",
        description="generates questions",
        type="list[str]",
    )
    output_parser = StructuredOutputParser.from_response_schemas([questions_schema])
    format_instructions = output_parser.get_format_instructions()

    user_prompt_template = """```Difficulty Level - {difficulty_level}\nTheme - {theme}\nActivity Type - {activity_type}\nPassage - {passage}```"""

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
        difficulty_level=english_question_params.difficulty_level,
        theme=english_question_params.theme,
        activity_type=english_question_params.activity_type,
        passage=english_question_params.passage,
        format_instructions=format_instructions,
    ).to_messages()

    return StreamingResponse(
        call_openai_chat_model(messages, model=model, max_tokens=1024, streaming=True),
        media_type="text/event-stream",
    )
