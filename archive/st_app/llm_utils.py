import json

import streamlit as st
import openai

openai.api_key = "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"


def create_system_prompt(subject, topics, topic):
    system_prompt = ""
    system_prompt += "You are EducationGPT, a very helpful educational assistant. You are very good at course planning, design and analysis. You can understand what is the best way to ensure a learner has understood some key concepts in any subject and can create effective course content and assessments to facilitate this\n\n"
    system_prompt += f'The subject of the course is "{subject}"\n'
    system_prompt += "The topics for this course are:\n"

    for topic_text in topics:
        system_prompt += f"- {topic_text}\n"

    system_prompt += f'\nThe topic we are currently focusing on is "{topic}"\n\n'
    system_prompt += """Bloom's Taxonomy is a very useful tool for guiding assessment creation for any subject. We want to create assessments that target the following level of Bloom's Taxonomy:

Knowledge:
This is related to remembering or recalling the information. Generally, the verbs used in this level are: Define, list, name, recall, state, recognize, and so forth. Specifically for computer science subjects, a learner's competency at this level can be assessed by asking them to define a particular method, recall syntax, recognize a specific concept present in some code, etc.

Comprehension:
This is related to recalling and interpreting facts. Commonly used verbs at this level are: summarize, understand, comprehend, explain, generalize, interpret, predict, summarize, and translate. Learners should understand the function and behaviors of each structure. Specifically for computer science subjects, a learner's competency at this level can be assessed by asking them to translate an algorithm from one form to another, explaining how a certain code snippet works, translating a code snippet into another language, etc."""

    return system_prompt


def parse_questions(chat_text):
    prompt = chat_text + "\n\n"
    prompt += """Parse these questions and criteria into a JSON with the following format:
[
    {
        "question": str,
        "criteria": [str, str, str...]
    }
]

JSON:"""

    response = openai.Completion.create(
        model="text-davinci-003", prompt=prompt, max_tokens=1024, temperature=0
    )

    questions_json_str = response["choices"][0]["text"].strip()
    questions_json = json.loads(questions_json_str)

    return questions_json


@st.cache_data
def get_questions(subject, all_topics, topic, bloom_level):
    system_prompt = create_system_prompt(subject, topic, all_topics)

    question_message = f'Create assessment questions for the subject "{subject}" and the topic "{topic}" with respect to the "{bloom_level}" level of Bloom\'s Taxonomy. Here are some guidelines to follow which creating the assessment questions:\n- Make sure you are creating the questions within this particular topic and not the other topics.\n- The question needs to promote effortful thinking and establish that the learner has really understood the underlying concepts.\n- If there are any code snippets in the question annotate them with ```.\n- Frame questions such that the required answer can be written in very few words.\n- The assessments will be open book in nature so ask questions that can really test understanding of concepts even if the learners are allowed to refer to educational material.\n\nCreate 5 questions.'
    criteria_message = 'For each of these questions, provide detailed and objective evaluation criteria which will be used to evaluate the learner\'s answers. Here are some guidelines to follow while creating the criteria:\n- This will be in the form of a list of around 4-5 criteria for each question.\n- These criteria should approximately be of equal importance.\n- These criteria should effectively describe levels of expected performance for the assessment.\n- Describe demonstrable behavior; do not describe the learner.\n- Avoid vague terms that are open to subjective interpretation such as "critical," "appropriate," "excellent" and "analytical."'

    messages = [{"role": "user", "content": system_prompt + "\n\n" + question_message}]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.5
    )
    chat_question_completion = response["choices"][0]["message"]["content"]

    messages.append({"role": "assistant", "content": chat_question_completion})
    messages.append({"role": "user", "content": criteria_message})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo", messages=messages, temperature=0.5
    )
    chat_criteria_completion = response["choices"][0]["message"]["content"]

    questions = parse_questions(
        chat_question_completion + "\n" + chat_criteria_completion
    )

    return questions


def parse_evaluation(criteria_evaluation_text):
    prompt = criteria_evaluation_text + "\n\n"
    prompt += """Parse this into a JSON with the following format:
[
    {
        "evaluation_result": bool,
        "reason": str
    }
]

JSON:"""

    response = openai.Completion.create(
        model="text-davinci-003", prompt=prompt, max_tokens=1024, temperature=0
    )
    criteria_evaluation_json_str = response["choices"][0]["text"].strip()
    criteria_evaluation_result = json.loads(criteria_evaluation_json_str)

    return criteria_evaluation_result


def evaluate_answer(question, answer, subject, topic):
    question_text = question["question"]
    criteria_list = question["criteria"]

    prompt = f'You are an expert in the subject "{subject}" and are currently facilitating an online learning program teaching this subject. The topic we are currently focusing on is "{topic}"\n\n.'
    prompt += f"Question: {question_text}\nStudent Answer: {answer}\n\n"
    prompt += "Evaluation Criteria:\n"
    for criteria_idx, criteria_text in enumerate(criteria_list):
        prompt += f"{criteria_idx + 1}. {criteria_text}\n"
    prompt += "\n"
    prompt += "For each of the provided evaluation criteria, mention if the student's answer has satisfied it, and why."

    response = openai.Completion.create(
        model="text-davinci-003", prompt=prompt, max_tokens=512, temperature=0.5
    )

    criteria_evaluation_text = response["choices"][0]["text"].strip()
    st.session_state.criteria_evaluation_text = criteria_evaluation_text
    criteria_evaluation_result = parse_evaluation(criteria_evaluation_text)

    prompt += "\n" + criteria_evaluation_text + "\n"
    prompt += "Provide some feedback for the student for this question. Make sure the feedback is as clear, objective and actionable as possible."

    response = openai.Completion.create(
        model="text-davinci-003", prompt=prompt, max_tokens=512, temperature=0.5
    )

    feedback_text = response["choices"][0]["text"].strip()

    return criteria_evaluation_result, feedback_text
