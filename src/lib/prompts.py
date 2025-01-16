import traceback
from typing import List, Dict
from pydantic import BaseModel, Field
from datetime import datetime
from langchain_core.output_parsers import PydanticOutputParser
from lib.llm import (
    call_llm_and_parse_output,
    call_openai_chat_model,
    get_llm_input_messages,
    COMMON_INSTRUCTIONS,
    logger,
)


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

    try:
        pred_dict = await call_llm_and_parse_output(
            llm_input_messages,
            model=model,
            output_parser=output_parser,
            api_key=api_key,
            max_tokens=2048,
            verbose=True,
            labels=["generate_answer"],
        )
        return pred_dict["solution"]
    except Exception as exception:
        traceback.print_exc()
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

    model = "gpt-4o-2024-11-20"

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
        raise exception


async def summarize_learner_insights(
    task_level_insights: List[str], system_prompt_template: str, api_key: str
) -> str:
    # system_prompt_template = """"You are an advanced learning analytics assistant tasked with integrating insights from multiple tasks to produce a single, comprehensive summary of a student's performance. Your focus is exclusively on identifying and elaborating on the areas where the student is struggling. Do not mention any strengths or positive aspects of the student’s performance—your analysis should solely target the challenges and deficiencies observed.\n\n**Instructions:**\n\n1. **Data Aggregation:**\n- Combine insights from various tasks and assignments to compile a complete picture of the student’s performance.\n- Ensure that all observations across different learning contexts are considered.\n\n2. **Identify Struggles in Content Comprehension:**\n- Highlight concepts, topics, or skills where the student consistently shows misunderstanding, misinterpretation, or difficulty.\n- Detail instances where incorrect reasoning, incomplete explanations, or repeated errors are evident.\n\n3. **Feedback Response and Behavioral Analysis:**\n- Analyze how the student utilizes—or fails to utilize—feedback from instructors. Emphasize patterns of recurring errors or a lack of improvement after corrections.\n- Note any issues related to timing, such as delayed responses or procrastination, along with patterns indicating low persistence or avoidance of complex problems.\n\n4. **Learning Strategy and Process Gaps:**\n- Identify ineffective learning habits, inadequate study methods, or strategic approaches that are contributing to poor outcomes.\n- Discuss any evidence of failure to seek clarifications or additional help when required.\n\n5. **Synthesize and Conclude:**\n- Produce a cohesive summary that integrates all the above points, presenting a clear, consolidated view of where the student is struggling.\n- Focus exclusively on the areas of difficulty without referencing any strengths or positive aspects in the summary.\n\n**Task:**\nUsing the provided multi-task insights, generate a comprehensive summary that details the specific areas where the student is struggling, integrating evidence from content comprehension, feedback response, behavioral patterns, and learning strategies."""

    user_prompt_template = """Task level insights:\n```\n{task_level_insights}\n```"""

    task_level_insights_str = "\n----------\n".join(task_level_insights)

    llm_input_messages = get_llm_input_messages(
        system_prompt_template,
        user_prompt_template,
        task_level_insights=task_level_insights_str,
    )

    model = "gpt-4o-2024-11-20"

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
        raise exception


async def async_index_wrapper(func, index, *args, **kwargs):
    output = await func(*args, **kwargs)
    return index, output
