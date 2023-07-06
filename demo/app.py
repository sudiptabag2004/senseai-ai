import streamlit as st
import requests
import json
from functools import partial

subject_col, topic_col, sub_topic_col = st.columns(3)

if "is_training_started" not in st.session_state:
    st.session_state.is_training_started = False

with subject_col:
    subject = st.selectbox(
        "Choose Subject",
        ["Javascript", "J2"],
        key="subject",
        disabled=st.session_state.is_training_started,
    )

with topic_col:
    topic = st.selectbox(
        "Choose Topic",
        ["Basics"],
        key="topic",
        disabled=st.session_state.is_training_started,
    )

with sub_topic_col:
    sub_topic = st.selectbox(
        "Choose Sub-topic",
        ["Operators"],
        key="sub_topic",
        disabled=st.session_state.is_training_started,
    )

blooms_level_col, learning_outcome_col = st.columns(2)

with blooms_level_col:
    blooms_level = st.selectbox(
        "Choose Bloom's Level",
        ["Analyzing"],
        key="blooms_level",
        disabled=st.session_state.is_training_started,
    )

with learning_outcome_col:
    learning_outcome = st.selectbox(
        "Choose Learning Outcome",
        [
            "Analyze complex expressions containing multiple operators, and break them down into simpler parts"
        ],
        key="learning_outcome",
        disabled=st.session_state.is_training_started,
    )


def on_start_training_click():
    st.session_state.is_training_started = True


def on_reset_training_click():
    st.session_state.is_training_started = False


if not st.session_state.is_training_started:
    st.button("Start Training", on_click=on_start_training_click)
else:
    st.button("Reset Training", on_click=on_reset_training_click)

is_training_started = st.session_state.is_training_started

with st.expander("See variables"):
    st.session_state


def delete_user_chat_message(index_to_delete: int):
    # delete both the user message and the AI assistant's response to it
    updated_chat_history = st.session_state.chat_history[:index_to_delete]
    updated_ai_chat_history = st.session_state.ai_chat_history[:index_to_delete]

    if index_to_delete + 2 < len(st.session_state.chat_history):
        updated_chat_history += st.session_state.chat_history[index_to_delete + 2 :]
        updated_ai_chat_history += st.session_state.ai_chat_history[
            index_to_delete + 2 :
        ]

    st.session_state.chat_history = updated_chat_history
    st.session_state.ai_chat_history = updated_ai_chat_history


if is_training_started:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "ai_chat_history" not in st.session_state:
        st.session_state.ai_chat_history = []

    chat_history = st.session_state.chat_history
    ai_chat_history = st.session_state.ai_chat_history

    if not chat_history:
        with st.chat_message("assistant"):
            with st.spinner("Generating question..."):
                question_generation_response = requests.post(
                    "http://127.0.0.1:8001/training/question",
                    data=json.dumps(
                        {
                            "topic": f"{subject} -> {topic} -> {sub_topic}",
                            "blooms_level": blooms_level,
                            "learning_outcome": learning_outcome,
                        }
                    ),
                )

            question_generation_response = question_generation_response.json()

            if not question_generation_response["success"]:
                st.error("Something went wrong. Please try again!")
                st.stop()

            generated_question = question_generation_response["question"]
            st.write(generated_question)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": generated_question}
            )
            st.session_state.ai_chat_history.append(
                {
                    "role": "assistant",
                    "content": f"Topic: {subject} -> {topic} -> {sub_topic}\nBlooms level: {blooms_level}\nLearning outcome: {learning_outcome}\nQuestion: {generated_question}",
                }
            )

    else:
        for index, message in enumerate(chat_history):
            with st.chat_message(message["role"]):
                if message["role"] == "assistant":
                    st.write(message["content"])
                else:
                    user_answer_cols = st.columns([7, 1])
                    user_answer_cols[0].write(message["content"])
                    user_answer_cols[1].button(
                        "Delete",
                        on_click=partial(
                            delete_user_chat_message, index_to_delete=index
                        ),
                        key=index,
                    )

    # reset AI response state
    if "ai_response_in_progress" not in st.session_state:
        st.session_state.ai_response_in_progress = False

    def toggle_ai_response_state():
        st.session_state.ai_response_in_progress = (
            not st.session_state.ai_response_in_progress
        )

    user_answer = st.chat_input(
        "Your answer",
        on_submit=toggle_ai_response_state,
        disabled=st.session_state.ai_response_in_progress,
    )

    if user_answer:
        with st.chat_message("user"):
            user_answer_cols = st.columns([7, 1])
            user_answer_cols[0].write(user_answer)
            user_answer_cols[1].button(
                "Delete",
                on_click=partial(
                    delete_user_chat_message, index_to_delete=len(chat_history)
                ),
                key=len(chat_history),
            )

        with st.chat_message("assistant"):
            ai_chat_history.append({"role": "user", "content": user_answer})

            with st.spinner("Fetching AI response..."):
                training_chat_response = requests.post(
                    "http://127.0.0.1:8001/training/chat",
                    data=json.dumps({"messages": ai_chat_history}),
                )

            if training_chat_response.status_code != 200:
                st.error("Something went wrong. Please try again!")
                # remove the last user input from ai_chat_history
                ai_chat_history.pop()
                st.stop()

            toggle_ai_response_state()
            training_chat_response = training_chat_response.json()

            user_answer_type = training_chat_response["type"]
            if user_answer_type == "irrelevant":
                ai_response = "Irrelevant question"
            elif user_answer_type == "clarification":
                # string clarification
                ai_response = training_chat_response["response"]
            else:
                # the response given is actually the answer to the question
                score = training_chat_response["response"]["answer"]
                if score == 2:
                    result = "Proficient :rocket:"
                elif score == 1:
                    result = "Almost there :runner:"
                elif score == 0:
                    result = "You can do better :hugging_face:"

                ai_response = f"Result: {result}  \nFeedback: {training_chat_response['response']['feedback']}"

            st.write(ai_response)

        # save last user message only if there is a assistant response as well
        st.session_state.chat_history += [
            {"role": "user", "content": user_answer},
            {"role": "assistant", "content": ai_response},
        ]

        ai_chat_history.append(
            {"role": "assistant", "content": json.dumps(training_chat_response)},
        )
        st.session_state.ai_chat_history = ai_chat_history
