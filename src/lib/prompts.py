import traceback
from typing import List, Dict, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import streamlit as st
import openai
import instructor
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages.utils import convert_to_openai_messages
from lib.llm import (
    call_llm_and_parse_output,
    call_openai_chat_model,
    get_llm_input_messages,
    COMMON_INSTRUCTIONS,
    logger,
)
from lib.audio import prepare_audio_input_for_ai
from models import TaskType, TaskInputType, TaskAIResponseType
from lib.config import openai_plan_to_model_name


async def generate_answer_for_task(
    task_name: str, task_description: str, task_context: str, model: str, api_key: str
) -> str:
    system_prompt_template = """You are a helpful and encouraging tutor.\n\n{input_description}\n\nYou need to work out your own solution to the task. You will use this solution later to evaluate the student's solution.\n\nImportant Instructions:\n- Give some reasoning before arriving at the answer but keep it concise.\n- Make sure to carefully read the task description and completely adhere to the requirements without making up anything on your own that is not already present in the description.{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name:\n```\n{task_name}\n```\n\nTask description:\n```\n{task_description}\n```"""
    llm_input_kwargs = {}
    input_description = "You will be given a task that has been assigned to a student along with its description."

    if task_context:
        user_prompt_template += f"""\n\nContext:\n```\n{task_context}\n```"""
        llm_input_kwargs["task_context"] = task_context
        input_description = "You will be given a task that has been assigned to a student along with its description and the context required to solve it."

    class Output(BaseModel):
        solution: str = Field(
            title="solution",
            description="The solution to the task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    client = instructor.from_openai(openai.OpenAI(api_key=api_key))

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        input_description=input_description,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
        **llm_input_kwargs,
    )

    llm_input_messages = convert_to_openai_messages(llm_input_messages)

    try:
        pred = client.chat.completions.create(
            model=model,
            messages=llm_input_messages,
            response_model=Output,
            max_completion_tokens=8096,
            top_p=1,
            temperature=0,
            frequency_penalty=0,
            presence_penalty=0,
            store=True,
        )

        pred_dict = pred.model_dump()

        message = f"model: {model} prompt: {llm_input_messages} response: {pred_dict}"
        logger.info(message)

        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()

        if "insufficient_quota" in str(exception):
            st.error(
                "Your OpenAI account credits have been exhausted. Please recharge your OpenAI account for you to continue using SensAI."
            )
            st.stop()

        raise exception


def convert_tests_to_prompt(tests: List[Dict]) -> str:
    if not tests:
        return ""

    return "\n-----------------\n".join(
        [f"Input:\n{test['input']}\n\nOutput:\n{test['output']}" for test in tests]
    )


async def generate_tests_for_task_from_llm(
    task_name: str,
    task_description: str,
    task_context: str,
    num_test_inputs: int,
    tests: List[Dict],
    model: str,
    api_key: str,
):
    system_prompt_template = """You are a test case generator for programming tasks.\n\n{input_description}\n\nYou need to generate a list of test cases in the form of input/output pairs.\n\n- Give some reasoning before arriving at the answer but keep it concise.\n- Create diverse test cases that cover various scenarios, including edge cases.\n- Ensure the test cases are relevant to the task description.\n- Provide at least 3 test cases, but no more than 5.\n- Ensure that every test case is unique.\n- If you are given a list of test cases, you need to ensure that the new test cases you generate are not duplicates of the ones in the list.\n{common_instructions}\n\nProvide the answer in the following format:\nLet's work this out in a step by step way to be sure we have the right answer\nAre you sure that's your final answer? Believe in your abilities and strive for excellence. Your hard work will yield remarkable results.\n<concise explanation>\n\n{format_instructions}"""

    user_prompt_template = """Task name:\n```\n{task_name}\n```\n\nTask description:\n```\n{task_description}\n```\n\nNumber of inputs: {num_test_inputs}\n\nTest cases:\n```\n{tests}\n```"""
    llm_input_kwargs = {}
    input_description = "You will be given a task name, its description, the number of inputs expected and, optionally, a list of test cases."

    if task_context:
        user_prompt_template += f"""\n\nContext:\n```\n{task_context}\n```"""
        llm_input_kwargs["task_context"] = task_context
        input_description = "You will be given a task name, its description, the number of inputs expected, the context required to solve the task and, optionally, a list of test cases."

    class TestCase(BaseModel):
        input: List[str] = Field(
            description="The list of inputs for a single test case. The number of inputs is {num_test_inputs}. Always return a list"
        )
        output: str = Field(description="The expected output for the test case")
        description: str = Field(
            description="A very brief description of the test case", default=""
        )

    class Output(BaseModel):
        test_cases: List[TestCase] = Field(
            description="A list of test cases for the given task",
        )

    output_parser = PydanticOutputParser(pydantic_object=Output)

    # import ipdb; ipdb.set_trace()

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        input_description=input_description,
        task_name=task_name,
        task_description=task_description,
        format_instructions=output_parser.get_format_instructions(),
        common_instructions=COMMON_INSTRUCTIONS,
        num_test_inputs=num_test_inputs,
        tests=convert_tests_to_prompt(tests),
        **llm_input_kwargs,
    )

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model,
            output_parser=output_parser,
            api_key=api_key,
            max_tokens=2048,
            verbose=True,
        )
        return [
            {
                "input": tc["input"],
                "output": tc["output"],
                "description": tc["description"],
            }
            for tc in pred_dict["test_cases"]
        ]
    except Exception as exception:
        traceback.print_exc()

        if "insufficient_quota" in str(exception):
            st.error(
                "Your OpenAI account credits have been exhausted. Please recharge your OpenAI account for you to continue using SensAI."
            )
            st.stop()

        raise exception


task_level_insights_base_prompt = """You are an advanced learning analytics assistant with expertise in cognitive psychology, educational theory, and data-driven learning analysis. Your task is to analyze the provided input—a chat history between a tutor and a student that includes detailed timestamps and responses for a given task along with the task details—to identify areas where the student is struggling. The analysis should consider both the specifics of the subject matter and the student’s behavioral and systemic learning patterns.

Instructions:

1. Content Comprehension Analysis:

- Conceptual Understanding: Use the chat transcript to pinpoint topics or concepts where the student consistently demonstrates confusion or misinterpretations. Look for instances where the student provides incorrect answers or seems unsure about critical concepts.
- Application Skills: Identify moments when the student is asked to apply a concept to a new problem or scenario. Evaluate the student's ability to transfer their understanding to these situations, noting any difficulties encountered.

2. Feedback Utilization:

- Responsiveness to Feedback: Analyze the tutor’s feedback alongside the student's subsequent responses. Determine if the student adjusts their approach based on the feedback provided or if similar errors recur.
- Attention to Detail: Look for patterns in the student’s responses that indicate whether they properly scrutinize the feedback or overlook crucial details in their learning process.

3. Behavioural Learning Patterns:

- Procrastination and Time Management: Examine the timestamps to assess if the student waits until the last minute to respond or if there are gaps that could indicate procrastination. Evaluate how these behaviors correlate with their understanding of the subject.
- Persistence and Resilience: Assess the student’s willingness to engage with difficult questions or challenges. Determine if the student shows perseverance by attempting follow-up questions or re-engaging with the material after a setback.
- Engagement and Study Habits: Evaluate the overall engagement level throughout the conversation. Look for signs of consistent study habits, such as detailed questions, clarification requests, or a proactive approach in seeking help.

4. Systemic and Strategic Factors:

- Learning Strategy: Based on the conversation, evaluate if the student employs effective strategies (such as breaking down problems, asking clarifying questions, or iterative problem-solving) or if they rely on less effective approaches.
- Resource Utilization: Consider how the student interacts with the tutor—are they making good use of the available guidance, or do they seem hesitant to ask for additional explanations when needed?
- Self-Monitoring: Look for evidence within the chat history that the student is actively monitoring their learning progress, such as asking for summaries, clarifications, or additional resources when encountering difficulties.

5. Recommendations:

- Based on your findings, provide targeted, actionable recommendations that address both subject-specific challenges and the student’s behavioral or systemic issues.
- Suggest strategies to improve concept understanding, responsiveness to feedback, time management, and overall study habits. Tailor your advice to the observed patterns and contextual evidence present in the chat history.

Additional Context:
- The input includes a detailed chat history between a tutor and the student with timestamps indicating the duration and frequency of interactions.
- Use both quantitative (e.g., response times, frequency of corrections) and qualitative (e.g., tone of responses, detailed explanations) evidence from the chat history to support your analysis.
- Focus only on the areas where the student is struggling.
- Avoid being overly verbose. Keep your feedback concise but always include examples to back up the struggles you have identified.

Task:
Analyze the provided chat history between the tutor and the student according to the above criteria. Identify key areas where the student is struggling, and conclude with specific, evidence-based recommendations tailored to the student’s learning behavior and subject-specific challenges. Avoid starting your response with a header/title for the task."""


insights_summary_base_prompt = """You are an advanced learning analytics assistant tasked with integrating insights from multiple tasks to produce a single, comprehensive summary of a student's performance. Your focus is exclusively on identifying and elaborating on the areas where the student is struggling. Do not mention any strengths or positive aspects of the student’s performance—your analysis should solely target the challenges and deficiencies observed.

**Instructions:**

1. **Data Aggregation:**
   - Combine insights from various tasks and assignments to compile a complete picture of the student’s performance.
   - Ensure that all observations across different learning contexts are considered.

2. **Identify Struggles in Content Comprehension:**
   - Highlight concepts, topics, or skills where the student consistently shows misunderstanding, misinterpretation, or difficulty.
   - Detail instances where incorrect reasoning, incomplete explanations, or repeated errors are evident.

3. **Feedback Response and Behavioral Analysis:**
   - Analyze how the student utilizes—or fails to utilize—feedback from instructors. Emphasize patterns of recurring errors or a lack of improvement after corrections.
   - Note any issues related to timing, such as delayed responses or procrastination, along with patterns indicating low persistence or avoidance of complex problems.

4. **Learning Strategy and Process Gaps:**
   - Identify ineffective learning habits, inadequate study methods, or strategic approaches that are contributing to poor outcomes.
   - Discuss any evidence of failure to seek clarifications or additional help when required.

5. **Synthesize and Conclude:**
   - Produce a cohesive summary that integrates all the above points, presenting a clear, consolidated view of where the student is struggling.
   - Focus exclusively on the areas of difficulty without referencing any strengths or positive aspects in the summary.

**Task:**
Using the provided multi-task insights, generate a comprehensive summary that details the specific areas where the student is struggling, integrating evidence from content comprehension, feedback response, behavioral patterns, and learning strategies. Avoid starting your response with a header/title for the task."""


async def generate_learner_insights_for_task(
    learner_task_chat_history: List[Dict],
    system_prompt_template: str,
    api_key: str,
    free_trial: bool,
) -> str:
    # system_prompt_template = """"You are an advanced learning analytics assistant with expertise in cognitive psychology, educational theory, and data-driven learning analysis. Your task is to analyze the provided input—a chat history between a tutor and a student that includes detailed timestamps and responses for a given task along with the task details—to identify areas where the student is struggling. The analysis should consider both the specifics of the subject matter and the student’s behavioral and systemic learning patterns.\n\nInstructions:\n\n1. Content Comprehension Analysis:\n\n- Conceptual Understanding: Use the chat transcript to pinpoint topics or concepts where the student consistently demonstrates confusion or misinterpretations. Look for instances where the student provides incorrect answers or seems unsure about critical concepts.\n- Application Skills: Identify moments when the student is asked to apply a concept to a new problem or scenario. Evaluate the student's ability to transfer their understanding to these situations, noting any difficulties encountered.\n\n2. Feedback Utilization:\n\n- Responsiveness to Feedback: Analyze the tutor’s feedback alongside the student's subsequent responses. Determine if the student adjusts their approach based on the feedback provided or if similar errors recur.\n- Attention to Detail: Look for patterns in the student’s responses that indicate whether they properly scrutinize the feedback or overlook crucial details in their learning process.\n\n3. Behavioural Learning Patterns:\n\n- Procrastination and Time Management: Examine the timestamps to assess if the student waits until the last minute to respond or if there are gaps that could indicate procrastination. Evaluate how these behaviors correlate with their understanding of the subject.\n- Persistence and Resilience: Assess the student’s willingness to engage with difficult questions or challenges. Determine if the student shows perseverance by attempting follow-up questions or re-engaging with the material after a setback.\n- Engagement and Study Habits: Evaluate the overall engagement level throughout the conversation. Look for signs of consistent study habits, such as detailed questions, clarification requests, or a proactive approach in seeking help.\n\n4. Systemic and Strategic Factors:\n\n- Learning Strategy: Based on the conversation, evaluate if the student employs effective strategies (such as breaking down problems, asking clarifying questions, or iterative problem-solving) or if they rely on less effective approaches.\n- Resource Utilization: Consider how the student interacts with the tutor—are they making good use of the available guidance, or do they seem hesitant to ask for additional explanations when needed?\n- Self-Monitoring: Look for evidence within the chat history that the student is actively monitoring their learning progress, such as asking for summaries, clarifications, or additional resources when encountering difficulties.\n\n5. Recommendations:\n\n- Based on your findings, provide targeted, actionable recommendations that address both subject-specific challenges and the student’s behavioral or systemic issues.\n- Suggest strategies to improve concept understanding, responsiveness to feedback, time management, and overall study habits. Tailor your advice to the observed patterns and contextual evidence present in the chat history.\n\nAdditional Context:\n- The input includes a detailed chat history between a tutor and the student with timestamps indicating the duration and frequency of interactions.\n- Use both quantitative (e.g., response times, frequency of corrections) and qualitative (e.g., tone of responses, detailed explanations) evidence from the chat history to support your analysis.\n- Focus only on the areas where the student is struggling.\n- Avoid being overly verbose. Keep your feedback concise but always include examples to back up the struggles you have identified.\n\nTask:\nAnalyze the provided chat history between the tutor and the student according to the above criteria. Identify key areas where the student is struggling, and conclude with specific, evidence-based recommendations tailored to the student’s learning behavior and subject-specific challenges."""

    user_prompt_template = """Task name:\n```\n{task_name}\n```\n\nTask description:\n```\n{task_description}\n```\n\nChat history:\n```\n{chat_history}\n```"""

    task_name = learner_task_chat_history[0]["task_name"]
    task_description = learner_task_chat_history[0]["task_description"]
    chat_history = "\n".join(
        [
            f"{chat['role']} ({datetime.fromisoformat(chat['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}): {chat['content']}"
            for chat in learner_task_chat_history
        ]
    )

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_name=task_name,
        task_description=task_description,
        chat_history=chat_history,
    )

    if free_trial:
        plan_type = "free_trial"
    else:
        plan_type = "paid"

    model = openai_plan_to_model_name[plan_type]["4o-text"]

    try:
        response = await call_openai_chat_model(
            llm_input_messages,
            model=model,
            api_key=api_key,
            max_tokens=10000,
            verbose=True,
        )
        return response
    except Exception as exception:
        traceback.print_exc()

        if "insufficient_quota" in str(exception):
            st.error(
                "Your OpenAI account credits have been exhausted. Please recharge your OpenAI account for you to continue using SensAI."
            )
            st.stop()

        raise exception


async def summarize_learner_insights(
    task_level_insights: List[str],
    system_prompt_template: str,
    api_key: str,
    free_trial: bool,
) -> str:
    # system_prompt_template = """"You are an advanced learning analytics assistant tasked with integrating insights from multiple tasks to produce a single, comprehensive summary of a student's performance. Your focus is exclusively on identifying and elaborating on the areas where the student is struggling. Do not mention any strengths or positive aspects of the student’s performance—your analysis should solely target the challenges and deficiencies observed.\n\n**Instructions:**\n\n1. **Data Aggregation:**\n- Combine insights from various tasks and assignments to compile a complete picture of the student’s performance.\n- Ensure that all observations across different learning contexts are considered.\n\n2. **Identify Struggles in Content Comprehension:**\n- Highlight concepts, topics, or skills where the student consistently shows misunderstanding, misinterpretation, or difficulty.\n- Detail instances where incorrect reasoning, incomplete explanations, or repeated errors are evident.\n\n3. **Feedback Response and Behavioral Analysis:**\n- Analyze how the student utilizes—or fails to utilize—feedback from instructors. Emphasize patterns of recurring errors or a lack of improvement after corrections.\n- Note any issues related to timing, such as delayed responses or procrastination, along with patterns indicating low persistence or avoidance of complex problems.\n\n4. **Learning Strategy and Process Gaps:**\n- Identify ineffective learning habits, inadequate study methods, or strategic approaches that are contributing to poor outcomes.\n- Discuss any evidence of failure to seek clarifications or additional help when required.\n\n5. **Synthesize and Conclude:**\n- Produce a cohesive summary that integrates all the above points, presenting a clear, consolidated view of where the student is struggling.\n- Focus exclusively on the areas of difficulty without referencing any strengths or positive aspects in the summary.\n\n**Task:**\nUsing the provided multi-task insights, generate a comprehensive summary that details the specific areas where the student is struggling, integrating evidence from content comprehension, feedback response, behavioral patterns, and learning strategies."""

    user_prompt_template = """Task level insights:\n```\n{task_level_insights}\n```"""

    task_level_insights_str = "\n----------\n".join(task_level_insights)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_level_insights=task_level_insights_str,
    )

    if free_trial:
        plan_type = "free_trial"
    else:
        plan_type = "paid"

    model = openai_plan_to_model_name[plan_type]["4o-text"]

    try:
        response = await call_openai_chat_model(
            llm_input_messages,
            model=model,
            api_key=api_key,
            max_tokens=10000,
            verbose=True,
        )
        return response
    except Exception as exception:
        traceback.print_exc()

        if "insufficient_quota" in str(exception):
            st.error(
                "Your OpenAI account credits have been exhausted. Please recharge your OpenAI account for you to continue using SensAI."
            )
            st.stop()

        raise exception


async def async_index_wrapper(func, index, *args, **kwargs):
    output = await func(*args, **kwargs)
    return index, output


async def generate_task_details_from_prompt(
    task_prompt: str,
    task_prompt_audio: bytes,
    api_key: str,
    free_trial: bool,
):
    class ScoringCriterion(BaseModel):
        category: str = Field(description="The name of the criterion")
        description: str = Field(description="A description of the criterion")
        min_score: int = Field(
            description="The minimum score for the criterion (e.g. 1)"
        )
        max_score: int = Field(
            description="The maximum score for the criterion (e.g. 5)"
        )

    class TaskConfig(BaseModel):
        reasoning: str
        type: Literal[
            TaskType.READING_MATERIAL, TaskType.QUESTION
        ]  # either "reading_material" or "question"
        name: str
        description: str

        # Fields specific to questions (optional for reading_material tasks)
        question_type: Optional[Literal["subjective", "objective"]] = None
        input_type: Optional[
            Literal[TaskInputType.CODING, TaskInputType.TEXT, TaskInputType.AUDIO]
        ] = None
        response_type: Optional[
            Literal[
                TaskAIResponseType.CHAT,
                TaskAIResponseType.EXAM,
                TaskAIResponseType.REPORT,
            ]
        ] = None
        coding_language: Optional[List[str]] = None
        scoring_criteria: Optional[List[ScoringCriterion]] = None
        answer: Optional[str] = None

        @field_validator("type")
        def validate_type(cls, v):
            if v not in [TaskType.READING_MATERIAL, TaskType.QUESTION]:
                raise ValueError(
                    f"type must be either '{TaskType.READING_MATERIAL}' or '{TaskType.QUESTION}'"
                )
            return v

        @field_validator("question_type", mode="after")
        def validate_question_type(cls, v, info):
            # Only validate question_type if the task is a question.
            if info.data.get("type") == TaskType.QUESTION:
                if v not in ["subjective", "objective"]:
                    raise ValueError(
                        'For questions, question_type must be either "subjective" or "objective"'
                    )
            return v

        @field_validator("input_type", mode="after")
        def validate_input_type(cls, v, info):
            if info.data.get("type") == TaskType.QUESTION:
                if v not in [
                    TaskInputType.CODING,
                    TaskInputType.TEXT,
                    TaskInputType.AUDIO,
                ]:
                    raise ValueError(
                        f'For questions, input_type must be "{TaskInputType.CODING}", "{TaskInputType.TEXT}", or "{TaskInputType.AUDIO}"'
                    )
            return v

        @field_validator("response_type", mode="after")
        def validate_response_type(cls, v, info):
            input_type = info.data.get("input_type")
            question_type = info.data.get("question_type")

            # If input_type is audio, response_type must be "audio".
            if input_type == TaskInputType.AUDIO and v != TaskAIResponseType.REPORT:
                raise ValueError(
                    f'For audio input, response_type must be "{TaskAIResponseType.REPORT}"'
                )
            # If input_type is code, response_type can only be "exam" or "chat".
            if input_type == TaskInputType.CODING and v not in [
                TaskAIResponseType.EXAM,
                TaskAIResponseType.CHAT,
            ]:
                raise ValueError(
                    f'For code input, response_type must be "{TaskAIResponseType.EXAM}" or "{TaskAIResponseType.CHAT}"'
                )
            # For subjective questions, response_type must always be "report".
            if question_type == "subjective" and v != TaskAIResponseType.REPORT:
                raise ValueError(
                    f'For subjective questions, response_type must be "{TaskAIResponseType.REPORT}"'
                )
            # For objective questions, response_type must be either "exam" or "chat".
            if question_type == "objective" and v not in [
                TaskAIResponseType.EXAM,
                TaskAIResponseType.CHAT,
            ]:
                raise ValueError(
                    f'For objective questions, response_type must be "{TaskAIResponseType.EXAM}" or "{TaskAIResponseType.CHAT}"'
                )
            return v

        class Config:
            json_schema_extra = {
                "example": {
                    "reasoning": "The user asked to generate a question to calculate a sum of two numbers",
                    "type": str(TaskType.QUESTION),
                    "name": "Calculate the Sum",
                    "description": "What is the sum of 7 and 5?",
                    "question_type": "objective",
                    "input_type": str(TaskInputType.TEXT),
                    "response_type": str(TaskAIResponseType.EXAM),
                    "programming_languages": [],
                    "scoring_criteria": None,
                    "answer": "12",
                }
            }

    output_parser = PydanticOutputParser(pydantic_object=TaskConfig)
    format_instructions = output_parser.get_format_instructions()

    system_prompt = f""""You are an expert assistant for an educational learning platform. An educator has provided a prompt describing a task they want to create. Your job is to extract all relevant task details from the educator\'s prompt and output them as a well-formed JSON object.\n\nFollow these steps:\n\nDetermine Task Type:\n\nIdentify if the task is a "question" or "reading_material".\nNote: "reading_material" refers to content that a learner needs to read and is not an assessment.\nGenerate Task Name and Description:\n\nFor reading material:\nExtract or generate a task name.\nFor task description, if the educator has already provided the reading material, use that directly. If the educator requests modifications or asks for new content, generate the reading material according to their instructions.\nFor a question:\nExtract or generate a task name.\nThe task description must clearly include the question that the learner is supposed to answer. It is possible that the educator asks you to generate the question based on the details they provide. First, analyse if the prompt given by the educator includes the question itself or instructions for generating the question. If the prompt includes instructions to generate the question, you must include the generated question details in the task description. Include all parts of the question in the description including any options provided or anything else that must be considered a part of the question. The task description should have all the details required to answer the question.\nDetermine Question Specifics (if the task is a question):\n\nIdentify whether the question is subjective (open-ended, not a fixed right answer) or objective (has a fixed correct answer). Store this in the key question_type with the value "subjective" or "objective".\nDetermine the Input Type:\n\nIdentify the type of input the learner needs to provide, and set input_type accordingly. Allowed values are:\n"coding"\n"text"\n"audio"\nDetermine the Response Type:\n\nDecide how the educator wants the AI to respond, and set response_type accordingly:\nIf input_type is "audio", then response_type must be "audio".\nIf input_type is "coding", then response_type can only be "exam" or "chat".\nFor subjective questions, response_type must always be "report".\nFor objective questions with a fixed answer, response_type must be either "chat" or "exam", as specified.\nProgramming Languages (if applicable):\n\nIf the task involves code and specific programming languages are mentioned, extract and list them in a key called programming_languages. Only include languages that match exactly one of the following:\n"HTML"\n"CSS"\n"Javascript"\n"NodeJS"\n"Python"\n"React"\n"SQL"\nScoring Criteria (for Subjective Questions):\n\nIf the question is subjective and the educator has provided a scoring criteria, extract it and include it under the key `scoring_criteria` in the output.\nIf no scoring criteria is given, generate a reasonable scoring criteria.\nScoring criteria must always be present for subjective questions and never be present for objective questions. If the educator has given a range of scores for each criterion, use them. Or generate a reasonable value for the range of scores for each criterion.\n\nCorrect Answer (for Objective Questions):\n\nIf the question is objective and a correct answer is provided in the educator\'s prompt, extract it and include it under the key `answer`. If the question is a multiple choice objective question, make sure that the correct answer includes the details for the correct option as well.\n\nAlways analyse the prompt based on the instructions provided first and give your reasoning before giving the final output.\n\n{format_instructions}"""

    if free_trial:
        plan_type = "free_trial"
    else:
        plan_type = "paid"

    llm_input_messages = [
        {"role": "system", "content": system_prompt},
    ]

    if task_prompt_audio:
        model = openai_plan_to_model_name[plan_type]["4o-audio"]
        user_message_content = [
            {
                "type": "text",
                "text": "```\nTask prompt\n```",
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": prepare_audio_input_for_ai(task_prompt_audio),
                    "format": "wav",
                },
            },
        ]
        if task_prompt:
            user_message_content.append({"type": "text", "text": task_prompt})

        llm_input_messages.append({"role": "user", "content": user_message_content})
    else:
        model = openai_plan_to_model_name[plan_type]["4o-text"]

        user_prompt_template = f"""```\n{task_prompt}\n```"""
        llm_input_messages.append({"role": "user", "content": user_prompt_template})

    client = instructor.from_openai(openai.OpenAI(api_key=api_key))

    try:
        pred = client.chat.completions.create(
            model=model,
            messages=llm_input_messages,
            response_model=TaskConfig,
            max_completion_tokens=8096,
            top_p=1,
            temperature=0,
            frequency_penalty=0,
            presence_penalty=0,
            store=True,
        )

        pred_dict = pred.model_dump()

        if pred_dict.get("scoring_criteria"):
            for criterion in pred_dict["scoring_criteria"]:
                criterion["range"] = [
                    criterion.pop("min_score"),
                    criterion.pop("max_score"),
                ]

        message = f"model: {model} prompt: {llm_input_messages} response: {pred_dict}"
        logger.info(message)

        return pred_dict
    except Exception as exception:
        traceback.print_exc()

        if "insufficient_quota" in str(exception):
            st.error(
                "Your OpenAI account credits have been exhausted. Please recharge your OpenAI account for you to continue using SensAI."
            )
            st.stop()

        raise exception
