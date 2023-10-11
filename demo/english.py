import json
import re
from functools import partial
from typing import Optional
import requests
from collections import defaultdict
import streamlit as st
import numpy as np
import pandas as pd
from streamlit_sortables import sort_items

activities_df = pd.read_csv("./english/sensai_english_activities.csv")
questions_df = pd.read_csv("./english/sensai_english_questions.csv")

level_to_level_name_map = {
    "A1": "Beginner",
    "A2": "Pre Intermediate",
    "B1": "Intermediate",
    "B2": "Upper Intermediate",
    "C1": "Advanced",
}

activity_levels = activities_df["Level"].unique().tolist()
activity_types = activities_df["Type"].unique().tolist()

if "is_training_started" not in st.session_state:
    st.session_state.is_training_started = False

activity_level = st.sidebar.selectbox(
    "Choose the activity level",
    activity_levels,
    disabled=st.session_state.is_training_started,
)
activity_level_name = level_to_level_name_map[activity_level]
activity_type = st.sidebar.selectbox(
    "Choose the activity type",
    activity_types,
    disabled=st.session_state.is_training_started,
)

shortlisted_activities = json.loads(
    activities_df[
        (activities_df["Level"] == activity_level)
        & (activities_df["Type"] == activity_type)
    ].to_json(orient="records")
)

selected_activity = st.sidebar.selectbox(
    "Choose the activity",
    shortlisted_activities,
    format_func=lambda row: row["Name"],
    disabled=st.session_state.is_training_started,
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "ai_chat_history" not in st.session_state:
    st.session_state.ai_chat_history = []

if "is_question_answered" not in st.session_state:
    st.session_state.is_question_answered = False


def reset_chat_history():
    st.session_state.chat_history = []
    st.session_state.ai_chat_history = []
    st.session_state.is_question_answered = False


def on_start_training_click():
    st.session_state.is_training_started = True


def on_reset_training_click():
    st.session_state.is_training_started = False

    if "question_element_type" in st.session_state:
        st.session_state.pop("question_element_type")

    if "selected_question" in st.session_state:
        st.session_state.pop("selected_question")

    reset_chat_history()


if not st.session_state.is_training_started:
    st.sidebar.button("Start Training", on_click=on_start_training_click)
else:
    st.sidebar.button("Reset Training", on_click=on_reset_training_click)

is_training_started = st.session_state.is_training_started

if not is_training_started:
    st.stop()

st.write("##### Description")
st.write(selected_activity["Description"])

activity_questions_df = questions_df[
    questions_df["Activity Index"] == selected_activity["index"]
]

instruction = activity_questions_df[
    activity_questions_df["Element Type"] == "Instruction"
].iloc[0]

st.write("##### Instruction")
st.write(instruction["Text"])

task_categories = [
    group
    for group in activity_questions_df["Element Type"].values
    if "task" in group.lower()
]

question_element_options = ["Preparation"] + np.unique(task_categories).tolist()

if "question_element_type" not in st.session_state:
    st.session_state.question_element_type = question_element_options[0]

question_element_type_index = question_element_options.index(
    st.session_state.question_element_type
)


def reset_question():
    # reset the question index marked as selected
    st.session_state.pop("selected_question")


def toggle_question_element_type():
    reset_question()
    reset_chat_history()


question_element_type = st.selectbox(
    "Choose your poison",
    question_element_options,
    on_change=toggle_question_element_type,
    key="question_element_type",
)

if activity_type == "Writing" or question_element_type == "Preparation":
    general_setup_prompt = "You will be given an english learning activity level and activity name along with a question that the student needs to be tested on, the actual solution to the question and a series of interactions between a student and you."
    evaluator_setup_prompt = "You will be given an english learning activity level and activity name along with a question that the student needs to be tested on, the student's response to the question and the actual solution."
else:
    general_setup_prompt = "You will be given an english learning activity level, activity name and context along with a question based on the context that the student needs to be tested on, the actual solution to the question and a series of interactions between a student and you."
    evaluator_setup_prompt = "You will be given an english learning activity level, activity name and context along with a question based on the context that the student needs to be tested on, the student's response to the question and the actual solution."

question_element_df = activity_questions_df[
    activity_questions_df["Element Type"] == question_element_type
]

questions = json.loads(question_element_df.to_json(orient="records"))

if "selected_question" not in st.session_state:
    st.session_state.selected_question = (0, questions[0])

print(type(st.session_state.selected_question))
selected_question_index = st.session_state.selected_question[0]

if len(questions) > 1:
    _, row = st.selectbox(
        "Select Question",
        enumerate(questions),
        format_func=lambda val: f"Question {val[0] + 1}",
        on_change=reset_chat_history,
        key="selected_question",
    )
else:
    row = questions[0]

st.write(f'Question Type: `{row["Question Type"]}`')

if question_element_type in task_categories:
    if activity_type == "Listening":
        audio_path = f'./english/media/{activity_level}/{activity_type}/{selected_activity["index"]}.mp3'
        st.audio(audio_path)

        with st.expander("Transcript"):
            transcription = activity_questions_df[
                activity_questions_df["Element Type"] == "Transcript"
            ]["Text"].values[0]
            st.write(transcription)
    else:
        image_df = activity_questions_df[
            activity_questions_df["Element Type"] == "Image"
        ]
        text_df = activity_questions_df[activity_questions_df["Element Type"] == "Text"]

        if len(image_df):
            image_path = f'./english/media/{activity_level}/{activity_type}/{selected_activity["index"]}.png'
            st.image(image_path)
            activity_text = image_df["Text"].values[0]
        else:
            activity_text = text_df["Text"].values[0]
            st.write(activity_text)

chat_history = st.session_state.chat_history
ai_chat_history = st.session_state.ai_chat_history

question = row["Question"]
answer_key = row["Key"]


def escape_markdown(text):
    # Define a dictionary of characters that need to be escaped in Markdown
    markdown_special_chars = {
        "\\": "\\\\",
        "`": "\\`",
        "*": "\\*",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "[": "\\[",
        "]": "\\]",
        "(": "\\(",
        ")": "\\)",
        ">": "\\>",
        "#": "\\#",
        "+": "\\+",
        "-": "\\-",
        ".": "\\.",
        "!": "\\!",
    }

    # Create a regular expression pattern to match any of the special characters
    pattern = "|".join(re.escape(char) for char in markdown_special_chars.keys())

    # Use re.sub to replace special characters with their escaped counterparts
    escaped_text = re.sub(pattern, lambda x: markdown_special_chars[x.group()], text)

    return escaped_text


if row["Question Type"] == "Matching":
    raw_groups = row["Groups"].split("\n")
    raw_groups = [
        f"{chr(97 + index)}) {group}" for index, group in enumerate(raw_groups)
    ]

    groups = "\n".join(raw_groups)
    question += f"\n\nGroups:\n\n{groups}\n"

    # update answer key
    true_matches = answer_key.split("\n")
    # remove empty values
    true_matches = [match for match in true_matches if match]
    formatted_matches = []

    for group_index, group_matches in enumerate(true_matches):
        for group_match in group_matches:
            formatted_matches.append(f"{group_match}: {chr(97 + group_index)}")

    answer_key = ", ".join(formatted_matches)

if row["Question Type"] in ["Ordering", "MCQ", "Checkbox", "Matching"]:
    raw_options = row["Values"].split("\n")
    # remove empty values
    raw_options = [option for option in raw_options if option]

    options = [
        f"{index + 1}) {escape_markdown(option)}"
        for index, option in enumerate(raw_options)
    ]
    num_options = len(options)
    options = "\n".join(options)

    question += f"\nOptions:\n\n{options}"

if row["Question Type"] == "Matching":
    question += "\n\nSelect the correct group for each option from the dropdowns below (i.e. a, b, etc.)"


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
    st.session_state.is_question_answered = False


if not chat_history:
    st.session_state.chat_history.append({"role": "assistant", "content": question})

    if activity_type == "Writing" or question_element_type == "Preparation":
        ai_history_base_message = f"```Activity Level - {activity_level_name}\n\nActivity Name - {selected_activity['Name']}\n\nQuestion - {question}\n\nActual Solution - {answer_key}```"
    else:
        context = None
        if activity_type == "Listening":
            context = transcription
        else:
            context = activity_text
        ai_history_base_message = f"```Activity Level - {activity_level_name}\n\nActivity Name - {selected_activity['Name']}\n\nContext - {context}\n\nQuestion - {question}\n\nActual Solution - {answer_key}```"

    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_history_base_message,
            "type": "question",
        }
    )

    with st.chat_message("assistant"):
        st.write(question)

else:
    for index, message in enumerate(chat_history):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.write(message["content"])
            else:
                user_response_display_cols = st.columns([7, 1])
                user_response_display_cols[0].write(message["content"])
                user_response_display_cols[1].button(
                    "Delete",
                    on_click=partial(delete_user_chat_message, index_to_delete=index),
                    key=f"delete_response_{index}",
                )

# reset AI response state
if "ai_response_in_progress" not in st.session_state:
    st.session_state.ai_response_in_progress = False


def toggle_ai_response_state():
    st.session_state.ai_response_in_progress = (
        not st.session_state.ai_response_in_progress
    )


# if row["Question Type"] == "Ordering":
#     user_answer = st.chat_input(
#         "Your answer",
#         on_submit=toggle_ai_response_state,
#         disabled=st.session_state.ai_response_in_progress,
#     )
# else:


user_answer_ai = ""
user_answer_chat = ""

if not st.session_state.is_question_answered:
    response_container = st.empty()

    if not st.session_state.ai_response_in_progress:
        if row["Question Type"] == "Matching":
            response_cols = response_container.columns(num_options)

            for answer_col_index, answer_col in enumerate(response_cols):
                answer_col.selectbox(
                    f"Option: {answer_col_index + 1}",
                    [f"{chr(97 + index)}" for index in range(len(raw_groups))],
                    key=f"user_response_matching_{answer_col_index}",
                )

        elif row["Question Type"] == "MCQ":
            st.selectbox(
                f"Select the correct option",
                [f"{index + 1}" for index in range(num_options)],
                key=f"user_response_mcq",
            )

        elif row["Question Type"] == "Checkbox":
            options_to_choose_from = [
                {"index": index, "value": option}
                for index, option in enumerate(raw_options)
            ]

            st.multiselect(
                "Select all the correct options below",
                options_to_choose_from,
                format_func=lambda row: row["value"],
                key=f"user_response_checkbox",
            )

        elif row["Question Type"] == "Ordering":
            options_to_choose_from = [
                {"index": index, "value": option}
                for index, option in enumerate(raw_options)
            ]

            # if ordering_response_key and ordering_response_key in st.session_state:
            #     st.session_state.pop(ordering_response_key)

            sort_items(
                raw_options,
                "Select the options in the correct order",
                key="user_response_ordering",
            )

        is_user_response_submit = st.button(
            "Submit",
            type="primary",
            on_click=toggle_ai_response_state,
            key="user_responses_submit",
        )

    if (
        "user_responses_submit" in st.session_state
        and st.session_state.user_responses_submit
    ):
        response_container.empty()

        if row["Question Type"] == "Matching":
            user_answer_chat = ""

            group_response_dict = defaultdict(list)
            for index in range(num_options):
                group_index = (
                    ord(st.session_state[f"user_response_matching_{index}"]) - 97
                )
                group_response_dict[raw_groups[group_index]].append(raw_options[index])

            for group in raw_groups:
                group_options = group_response_dict[group]
                user_answer_chat += f"{group}:\n"
                user_answer_chat += ",".join(group_options)
                user_answer_chat += "\n\n"

            user_answer_chat = user_answer_chat.strip()

            user_answer_ai = ",".join(
                [
                    f"{index + 1}: {st.session_state[f'user_response_matching_{index}']}"
                    for index in range(num_options)
                ]
            )
        elif row["Question Type"] == "MCQ":
            user_answer_ai = st.session_state[f"user_response_mcq"]
            user_answer_chat = raw_options[int(user_answer_ai) - 1]
        elif row["Question Type"] == "Checkbox":
            options_selected = st.session_state[f"user_response_checkbox"]

            user_answer_chat = ",".join(
                [option["value"] for option in options_selected]
            )
            user_answer_ai = ",".join(
                [str(option["index"] + 1) for option in options_selected]
            )

        elif row["Question Type"] == "Ordering":
            options_selected = st.session_state[f"user_response_ordering"][0]["items"]

            user_answer_chat = "\n".join(
                [
                    f"{index + 1}. {option}"
                    for index, option in enumerate(options_selected)
                ]
            )

            user_answer_ai = ",".join(
                [str(raw_options.index(option) + 1) for option in options_selected]
            )
else:

    def move_to_next_question():
        if selected_question_index == len(questions) - 1:
            # all questions done within the same question element type

            if question_element_type_index == len(question_element_options) - 1:
                # all questions done within the module
                return
            else:
                # move to the next element type within the module
                st.session_state.question_element_type = question_element_options[
                    question_element_type_index + 1
                ]
                # reset the question index being marked as selected
                reset_question()
        else:
            # within the same question element type, move to the next questions
            st.session_state.selected_question = (
                selected_question_index + 1,
                questions[selected_question_index + 1],
            )

        reset_chat_history()

    if question_element_type_index == len(question_element_options) - 1:
        # all questions done within the module
        st.success(
            "No more questions remaining in this module. Please select the next module from the sidebar."
        )

    is_user_response_submit = st.button(
        "Move to Next Question",
        type="primary",
        on_click=move_to_next_question,
        key="move_to_next_question",
    )

if user_answer_ai:
    with st.chat_message("user"):
        user_response_display_cols = st.columns([7, 1])
        user_response_display_cols[0].write(user_answer_chat)
        user_response_display_cols[1].button(
            "Delete",
            on_click=partial(
                delete_user_chat_message, index_to_delete=len(chat_history)
            ),
            key=f"delete_response_{len(chat_history)}",
        )

    with st.chat_message("assistant"):
        ai_chat_history.append({"role": "user", "content": user_answer_ai})

        with st.spinner("Fetching AI response..."):
            training_chat_response = requests.post(
                "http://127.0.0.1:8001/training/chat",
                data=json.dumps(
                    {
                        "messages": ai_chat_history,
                        "general_setup": general_setup_prompt,
                        "evaluator_setup": evaluator_setup_prompt,
                        "is_solution_provided": True,
                    }
                ),
                stream=True,
            )

        ai_response_placeholder = st.empty()
        ai_response = ""
        user_answer_type = None

        chunk_history = ""
        user_answer_score = None
        user_answer_feedback = None
        special_character_count = defaultdict(int)

        ai_response_placeholder.write("▌")
        for line in training_chat_response.iter_content(chunk_size=20):
            # first chunk is the user answer type
            if user_answer_type is None:
                user_answer_type = line.decode()
                print(user_answer_type)
                continue

            chunk = line.decode()
            chunk_history += chunk

            if user_answer_type in ["clarification", "miscellaneous"]:
                ai_response += chunk
                ai_response_placeholder.write(ai_response + "▌")

            elif user_answer_type == "answer":
                if "```" in chunk and not special_character_count["{"]:
                    continue

                if "{" in chunk:
                    special_character_count["{"] += 1

                if "}" in chunk:
                    special_character_count["{"] -= 1
                    if not special_character_count["{"]:
                        continue

                if "answer_evaluation" not in chunk_history:
                    continue

                if 'feedback": "' not in chunk_history:
                    if user_answer_score is not None:
                        continue
                    try:
                        user_answer_score = int(chunk)
                        if user_answer_score == 2:
                            result = "Proficient :rocket:"
                        elif user_answer_score == 1:
                            result = "Almost there :runner:"
                        elif user_answer_score == 0:
                            result = "You can do better :hugging_face:"
                        ai_response += f"Result - {result} \nFeedback - "
                        ai_response_placeholder.write(ai_response + "▌")
                    except:
                        continue
                else:
                    ai_response += chunk
                    ai_response_placeholder.write(ai_response + "▌")

        toggle_ai_response_state()

        if user_answer_type == "irrelevant":
            ai_response = "Irrelevant response"

        ai_response_placeholder.write(ai_response)

    # save last user message only if there is a assistant response as well
    st.session_state.chat_history += [
        {"role": "user", "content": user_answer_chat},
        {"role": "assistant", "content": ai_response},
    ]

    # update type of user message
    ai_chat_history[-1]["type"] = user_answer_type

    ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_response,
            "type": "response",
        },
    )
    st.session_state.ai_chat_history = ai_chat_history

    if user_answer_score is not None and user_answer_score == 2:
        st.session_state.is_question_answered = True

    st.experimental_rerun()
