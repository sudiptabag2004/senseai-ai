import os
import json

import streamlit as st

from llm_utils import get_questions, evaluate_answer

SUBJECTS_PATH = "./../local_data/subjects/"


def get_all_subjects():
    subjects = os.listdir(SUBJECTS_PATH)
    return subjects


def load_subject(subject):
    subject_path = os.path.join(SUBJECTS_PATH, subject)
    subject_roadmap = os.path.join(subject_path, "roadmap.json")
    subject_roadmap = json.load(open(subject_roadmap, "r"))

    all_topics = []
    for topic in subject_roadmap:
        all_topics.append(topic["topic_name"])

    return subject_roadmap, all_topics


def start_assessment():
    if st.session_state.current_assessment["status"] == "not_started":
        st.session_state.current_assessment["status"] = "started"

        st.session_state.current_assessment["subject"] = st.session_state.subject
        st.session_state.current_assessment["all_topics"] = st.session_state.all_topics
        st.session_state.current_assessment["topic"] = st.session_state.topic
        st.session_state.current_assessment[
            "bloom_level"
        ] = st.session_state.bloom_level

        questions = get_questions(
            st.session_state.subject,
            st.session_state.topic,
            st.session_state.all_topics,
            st.session_state.bloom_level,
        )

        st.session_state.current_assessment["questions"] = questions
        st.session_state.current_assessment["question_idx"] = 0
        st.session_state.current_assessment["answers"] = []
        st.session_state.current_assessment["all_evaluation_reports"] = []


def next_question():
    st.session_state.answer_input = ""
    st.session_state.current_assessment["current_evaluation_report"] = None
    st.session_state.current_assessment["question_idx"] += 1

    if st.session_state.current_assessment["question_idx"] == len(
        st.session_state.current_assessment["questions"]
    ):
        st.session_state.current_assessment["status"] = "finished"


def submit_question():
    answer = st.session_state.answer_input
    question = st.session_state.current_assessment["questions"][
        st.session_state.current_assessment["question_idx"]
    ]
    criteria = question["criteria"]

    st.session_state.current_assessment["answers"].append(answer)
    criteria_eval_report, feedback_text = evaluate_answer(
        question,
        answer,
        st.session_state.current_assessment["subject"],
        st.session_state.current_assessment["topic"],
    )
    st.session_state.criteria_eval_report = criteria_eval_report

    current_evaluation_report = "Evaluation Report:\n"
    for criterion_idx, criterion in enumerate(criteria):
        current_evaluation_report += (
            criterion
            + ":\n"
            + "Result: "
            + str(criteria_eval_report[criterion_idx]["evaluation_result"])
            + "\nReason: "
            + criteria_eval_report[criterion_idx]["reason"]
            + "\n\n"
        )
    current_evaluation_report += "Feedback: " + feedback_text

    st.session_state.current_assessment["current_evaluation_report"] = current_evaluation_report
    st.session_state.current_assessment["all_evaluation_reports"].append(
        current_evaluation_report
    )
