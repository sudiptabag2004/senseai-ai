import streamlit as st
import requests
from functools import partial
import json
from collections import defaultdict

difficulty_col, themes_col, activity_col = st.columns(3)

if "is_training_started" not in st.session_state:
    st.session_state.is_training_started = False

difficulty_level = difficulty_col.selectbox(
    "Choose difficulty level",
    ["Beginner", "Intermediate", "Advanced"],
    key="difficulty_level",
    disabled=st.session_state.is_training_started,
)

theme = themes_col.selectbox(
    "Choose theme",
    ["Sports", "Movies", "Job readiness", "Social skills"],
    key="theme",
    disabled=st.session_state.is_training_started,
)

activity_type = activity_col.selectbox(
    "Choose activity type",
    ["Reading", "Listening"],
    key="activity_type",
    disabled=st.session_state.is_training_started,
)


if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []

if "passage_chat_index" not in st.session_state:
    st.session_state.passage_chat_index = None

if "question_chat_index" not in st.session_state:
    st.session_state.question_chat_index = None


def on_start_training_click():
    st.session_state.is_training_started = True


def reset_passage_state():
    st.session_state.passage_chat_index = None


def reset_question_state():
    st.session_state.question_chat_index = None


def on_reset_training_click():
    st.session_state.is_training_started = False
    st.session_state.chat_history = []
    st.session_state.ai_chat_history = []
    reset_passage_state()
    reset_question_state()


if not st.session_state.is_training_started:
    st.button("Start Training", on_click=on_start_training_click)
else:
    st.button("Reset Training", on_click=on_reset_training_click)


def get_english_passage():
    passage_response = requests.post(
        "http://127.0.0.1:8001/english/passage",
        data=json.dumps(
            {
                "difficulty_level": difficulty_level.lower(),
                "activity_type": activity_type.lower(),
                "theme": theme.lower(),
                "messages": st.session_state.ai_chat_history,
            }
        ),
        stream=True,
    )

    if passage_response.status_code != 200:
        st.error("Something went wrong")
        import ipdb

        ipdb.set_trace()
        st.stop()

    ai_response_placeholder = st.empty()
    ai_response = ""
    chunk_history = ""
    special_character_count = defaultdict(int)
    ai_response_type = ""
    ai_response_placeholder.write("▌")

    for line in passage_response.iter_content(chunk_size=20):
        chunk = line.decode()
        old_chunk_history = str(chunk_history)
        chunk_history += chunk
        print(chunk)

        if "```" in chunk and not special_character_count["{"]:
            continue

        if "{" in chunk:
            special_character_count["{"] += 1

        if "}" in chunk:
            special_character_count["{"] -= 1
            if not special_character_count["{"]:
                continue

        if '"type":' not in old_chunk_history:
            continue

        if '"' in chunk and not special_character_count['"']:
            special_character_count['"'] += 1
            continue

        if 'value": "' not in old_chunk_history and special_character_count['"']:
            # type can be broken across chunks too (like passage)
            if '"' in chunk:
                if ai_response_type == "passage":
                    st.session_state.passage_chat_index = len(
                        st.session_state.chat_history
                    )
                special_character_count['"'] = -1
            else:
                ai_response_type += chunk
        else:
            ai_response += chunk
            ai_response_placeholder.write(ai_response + "▌")

    # cleanup extra quotes and newline characters from the end of the streaming
    ai_response = ai_response.strip()
    ai_response = ai_response.strip('"')
    ai_response_placeholder.write(ai_response)

    # save last user message only if there is a assistant response as well
    st.session_state.chat_history += [
        {"role": "assistant", "content": ai_response},
    ]

    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_response,
            "type": ai_response_type,
        },
    )


def get_english_question():
    question_response = requests.post(
        "http://127.0.0.1:8001/english/question",
        data=json.dumps(
            {
                "difficulty_level": difficulty_level.lower(),
                "activity_type": activity_type.lower(),
                "theme": theme.lower(),
                "passage": st.session_state.ai_chat_history[-1]["content"],
            }
        ),
        stream=True,
    )

    if question_response.status_code != 200:
        st.error("Something went wrong")
        import ipdb

        ipdb.set_trace()
        st.stop()

    ai_response_placeholder = st.empty()
    ai_response = ""
    ai_response_placeholder.write("▌")

    for line in question_response.iter_content(chunk_size=20):
        chunk = line.decode()

        ai_response += chunk
        ai_response_placeholder.write(ai_response + "▌")

    # cleanup extra quotes and newline characters from the end of the streaming
    ai_response = ai_response.strip()
    ai_response = ai_response.strip('"')
    ai_response_placeholder.write(ai_response)

    st.session_state.question_chat_index = len(st.session_state.chat_history)

    # save last user message only if there is a assistant response as well
    st.session_state.chat_history += [
        {"role": "assistant", "content": ai_response},
    ]

    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_response,
            "type": "question",
        },
    )


is_training_started = st.session_state.is_training_started

if is_training_started:
    chat_history = st.session_state.chat_history
    ai_chat_history = st.session_state.ai_chat_history

    def delete_user_chat_message(index_to_delete: int):
        # delete both the user message and the AI assistant's response to it
        updated_chat_history = st.session_state.chat_history[:index_to_delete]
        updated_ai_chat_history = st.session_state.ai_chat_history[:index_to_delete]

        if (
            st.session_state.passage_chat_index
            and st.session_state.passage_chat_index < index_to_delete
        ):
            if index_to_delete + 2 < len(st.session_state.chat_history):
                updated_chat_history += st.session_state.chat_history[
                    index_to_delete + 2 :
                ]
                updated_ai_chat_history += st.session_state.ai_chat_history[
                    index_to_delete + 2 :
                ]

        else:
            # if the passage was given after this message, nothing after this message needs to be retained
            reset_passage_state()
            reset_question_state()

        st.session_state.chat_history = updated_chat_history
        st.session_state.ai_chat_history = updated_ai_chat_history

    # reset AI response state
    if "ai_response_in_progress" not in st.session_state:
        st.session_state.ai_response_in_progress = False

    def toggle_ai_response_state():
        st.session_state.ai_response_in_progress = (
            not st.session_state.ai_response_in_progress
        )

    if not chat_history:
        with st.chat_message("assistant"):
            get_english_passage()

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

        if not st.session_state.question_chat_index:
            toggle_ai_response_state()
            with st.chat_message("assistant"):
                get_english_question()

            toggle_ai_response_state()

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

        if not st.session_state.passage_chat_index:
            with st.chat_message("assistant"):
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_answer}
                )
                st.session_state.ai_chat_history.append(
                    {"role": "user", "content": user_answer}
                )

                get_english_passage()

            toggle_ai_response_state()

        st.experimental_rerun()
