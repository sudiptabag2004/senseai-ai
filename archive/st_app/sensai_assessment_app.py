import os
import json

import streamlit as st

from app_utils import (
    load_subject,
    get_all_subjects,
    start_assessment,
    submit_question,
    next_question,
)

if "current_assessment" not in st.session_state:
    st.session_state.current_assessment = {
        "status": "not_started",
        "subject": None,
        "all_topics": None,
        "topic": None,
        "bloom_level": None,
        "questions": None,
        "question_idx": None,
        "answers": None,
        "all_evaluation_reports": None,
        "current_evaluation_report": None,
    }

subjects = get_all_subjects()

st.title("Sensai Assessment PoC App")

st.header("Assessment")
if st.session_state.current_assessment["status"] == "not_started":
    question_placeholder = st.empty()
    answer_input = st.empty()
else:
    question_placeholder = st.text(
        st.session_state.current_assessment["questions"][
            st.session_state.current_assessment["question_idx"]
        ]["question"]
    )
    answer_input = st.text_area("Enter your answer here", key="answer_input")
    st.button("Submit", on_click=submit_question)

    if st.session_state.current_assessment["current_evaluation_report"] is not None:
        st.header("Evaluation Report")
        st.write(st.session_state.current_assessment["current_evaluation_report"])
        st.button("Next Question", on_click=next_question)

    if st.session_state.current_assessment["status"] == "finished":
        st.header("Final Evaluation Report")
        st.json(st.session_state.current_assessment["all_evaluation_reports"])

with st.sidebar:
    subject = st.selectbox("Select a subject", subjects, key="subject")

    subject_roadmap, all_topics = load_subject(subject)
    st.session_state.all_topics = all_topics

    st.header("Subject Roadmap:")
    st.json(subject_roadmap)

    topic = st.selectbox("Select a topic", all_topics, key="topic")

    bloom_level = st.selectbox(
        "Select a Bloom Level",
        [
            "Knowledge",
            "Comprehension",
            "Application",
            "Analysis",
            "Synthesis",
            "Evaluation",
        ],
        key="bloom_level",
    )

    st.button("Start Assessment", on_click=start_assessment)

    st.write(st.session_state)
