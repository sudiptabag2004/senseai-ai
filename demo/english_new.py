import streamlit as st
import requests
import io
from functools import partial
import json
from collections import defaultdict

difficulty_col, themes_col, activity_col = st.columns(3)

difficulty_to_grade_map = {
    "Beginner": "1-2",
    "Intermediate": "3-5",
    "Advanced": "6-8",
}

# st.session_state

passage_difficulty_to_learning_outcomes = {
    "Beginner": [
        "Length and Simplicity: The passage should be short, ideally one paragraph with 5-6 sentences, with simple sentence structures",
        "Basic Vocabulary: Use basic, grade level-appropriate vocabulary to ensure understanding"
        "Clear Narrative or Concept: The content should have a clear and straightforward narrative or concept, such as a simple story or a description of an everyday event",
    ],
    "Intermediate": [
        "Moderate Length: The passage should be longer, consisting of 2-3 paragraphs with 5-6 sentences each, to provide a reading challenge",
        "Expanded Vocabulary: Incorporate a wider range of vocabulary, including some challenging words, to aid vocabulary development",
        "Varied Sentence Structures: Use a mix of simple and compound sentences to introduce moderate complexity",
        "Introduction of Themes: Start to introduce themes or morals in the stories or concepts, encouraging students to think more deeply about the content",
    ],
    "Advanced": [
        "Increased Length and Complexity: The passage should be significantly longer, about 4-5 paragraphs, with complex sentence structures",
        "Advanced Vocabulary: Employ a rich and challenging vocabulary, including less common words and phrases",
        "Complex Themes and Ideas: The content should contain complex themes, morals, or advanced concepts, requiring deeper comprehension and critical thinking",
    ],
}

question_difficulty_to_learning_outcomes = {
    "Beginner": [
        "Use Words in Sentences: Able to use a difficult word from the passage in a sentence of their own",
        "Basic Comprehension: Able to answer a simple open ended question about the passage that tests their understanding of the content in 1 sentence",
        "Basic Comprehension: Able to answer a simple MCQ question about the passage that tests their understanding of the content",
        "Comprehensive Interpretation: Able to interpret the author's message or the moral of the story",
    ],
    "Intermediate": [
        "Summarization Skills: Able to summarize a paragraph or the entire passage in their own words",
        "Elaborate Comprehension: Able to answer a simple open ended question about the passage that tests their understanding of the content in 2-3 sentences",
        "Self Assessment: Learners should be able to self-assess their similarities or differences from the main character in the passage",
        "Vocabulary Enhancement: Able to find synonyms or antonyms for given words from the passage",
    ],
    "Advanced": [
        "Critical Analysis: Able to critically analyze themes, character motivations, and plot developments",
        "Contextual Vocabulary Usage: Able to use vocabulary from the passage in more complex sentences and different contexts",
    ],
}

difficulty_to_eval_criteria = {
    "Beginner": [
        "Grammar: Learners should be able to correctly use basic parts of speech (nouns, verbs, adjectives) from the passage",
        "Sentence Usage: Learners should construct simple sentences using words from the passage, paying attention to correct syntax",
        "Semantics: Learners should create sentences that are meaningful and contextually relevant to the passage",
    ],
    "Intermediate": [
        "Grammar: Learners should demonstrate understanding of more complex grammatical structures (like past tense, plurals) and sentence types (declarative, interrogative)",
        "Sentence Construction: Learners should be able to construct compound sentences using conjunctions from the passage",
        "Inferential Understanding: Able to make inferences based on the information provided in the passage",
    ],
    "Advanced": [
        "Grammar: Learners should demonstrate understanding of more complex grammatical structures (like past tense, plurals) and sentence types (declarative, interrogative)",
        "Sentence Construction: Learners should be able to construct compound sentences using conjunctions from the passage",
    ],
}

eval_difficulty_to_num_incorrect_attempts = {
    "Beginner": "Right answer only after 2 incorrect attempts",
    "Intermediate": "Right answer only after 4 incorrect attempts",
    "Advanced": "Right answer only after 4 incorrect attempts",
}


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


def reset_question_generated_state():
    st.session_state.question_chat_index = None


if "question_chat_index" not in st.session_state:
    reset_question_generated_state()


def reset_question_lo_index():
    st.session_state.question_learning_outcome_index = 0


if "question_learning_outcome_index" not in st.session_state:
    reset_question_lo_index()


def reset_question_answered_state():
    st.session_state.is_question_answered = False


if "is_question_answered" not in st.session_state:
    reset_question_answered_state()


def on_start_training_click():
    st.session_state.is_training_started = True


def reset_passage_state():
    st.session_state.passage_chat_index = None


def reset_question_state():
    reset_question_generated_state()
    reset_question_lo_index()
    reset_question_answered_state()


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
                "grade_level": difficulty_to_grade_map[difficulty_level],
                "learning_outcomes": passage_difficulty_to_learning_outcomes[
                    difficulty_level
                ],
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
        return

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

    ai_response_type = ai_response_type.strip()

    if ai_response_type == "passage" and activity_type == "Listening":
        with st.spinner("Preparing audio..."):
            print('here')
            response = requests.post(
                "http://127.0.0.1:8001/audio/tts",
                data=json.dumps(
                    {
                        "text": ai_response.replace("Transcript:\n\n", ""),
                    }
                ),
                stream=True,
            )

            # Create an in-memory bytes buffer
            audio_buffer = io.BytesIO()
            for chunk in response.iter_content(chunk_size=4096):
                audio_buffer.write(chunk)
            audio_buffer.seek(0)

            # response.stream_to_file("output.mp3")
            st.audio(audio_buffer)

        st.session_state.chat_history += [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "value": ai_response},
                    {"type": "audio", "value": audio_buffer},
                ],
            },
        ]

    else:
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


def get_english_evaluation():
    english_evaluation_response = requests.post(
        "http://127.0.0.1:8001/english/evaluation",
        data=json.dumps(
            {
                "difficulty_level": difficulty_level.lower(),
                "messages": st.session_state.ai_chat_history[
                    st.session_state.question_chat_index :
                ],
            }
        ),
        stream=True,
    )

    if english_evaluation_response.status_code != 200:
        st.error("Something went wrong")
        import ipdb

        ipdb.set_trace()
        return

    ai_response_placeholder = st.empty()
    ai_response = ""
    ai_feedback = ""
    user_answer_type = None

    chunk_history = ""
    user_answer_score = None
    user_answer_feedback = None
    special_character_count = defaultdict(int)

    ai_response_placeholder.write("▌")
    for line in english_evaluation_response.iter_content(chunk_size=20):
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
                ai_feedback += chunk
                ai_response_placeholder.write(ai_response + "▌")

    if user_answer_type == "irrelevant":
        ai_response = "Irrelevant response"

    ai_response_placeholder.write(ai_response)

    st.session_state.chat_history += [
        {"role": "assistant", "content": ai_response},
    ]

    # update type of user message
    st.session_state.ai_chat_history[-1]["type"] = user_answer_type

    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": ai_feedback if user_answer_type == "answer" else ai_response,
            "type": "response",
        },
    )
    if user_answer_score == 2:
        st.session_state.is_question_answered = True


def get_english_question():
    passage = st.session_state.ai_chat_history[-1]["content"]
    question_response = requests.post(
        "http://127.0.0.1:8001/english/question",
        data=json.dumps(
            {
                "difficulty_level": difficulty_level.lower(),
                "grade_level": difficulty_to_grade_map[difficulty_level],
                "theme": theme.lower(),
                "learning_outcome": question_difficulty_to_learning_outcomes[
                    difficulty_level
                ][st.session_state.question_learning_outcome_index],
                "passage": passage,
            }
        ),
        stream=True,
    )

    if question_response.status_code != 200:
        st.error("Something went wrong")
        import ipdb

        ipdb.set_trace()
        return

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

    evaluation_criteria = "\n- ".join(difficulty_to_eval_criteria[difficulty_level])
    st.session_state.ai_chat_history.append(
        {
            "role": "assistant",
            "content": f"Difficulty Level - {difficulty_level}\nGrade Level - {difficulty_to_grade_map[difficulty_level]}\nLanguage - English\nPassage - {passage}\nQuestion - {ai_response}\nEvaluation Criteria\n- {evaluation_criteria}",
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
        reset_question_answered_state()

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
                    if isinstance(message["content"], list):
                        for _content in message["content"]:
                            if _content["type"] == "text":
                                st.write(_content["value"])
                            elif _content["type"] == "audio":
                                st.audio(_content["value"])
                    else:
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

        if (
            st.session_state.passage_chat_index
            and not st.session_state.question_chat_index
        ):
            toggle_ai_response_state()
            with st.chat_message("assistant"):
                get_english_question()

            toggle_ai_response_state()

    if not st.session_state.is_question_answered:
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
                        {
                            "role": "user",
                            "content": user_answer,
                            "type": "interest_response",
                        }
                    )

                    get_english_passage()

                toggle_ai_response_state()

            else:
                with st.chat_message("assistant"):
                    st.session_state.chat_history.append(
                        {"role": "user", "content": user_answer}
                    )
                    st.session_state.ai_chat_history.append(
                        {
                            "role": "user",
                            "content": user_answer,
                        }
                    )

                    get_english_evaluation()

                toggle_ai_response_state()

            st.experimental_rerun()
    else:
        if (
            st.session_state.question_learning_outcome_index
            == len(question_difficulty_to_learning_outcomes[difficulty_level]) - 1
        ):
            st.success(
                "You've answered all questions. To practice more, click on `Reset Training` and select a different activity type or theme or difficulty level"
            )
            st.stop()

        def move_to_next_question():
            st.session_state.question_learning_outcome_index += 1

            # wipe out the generated question and the subsequent conversation from the chat history
            st.session_state.chat_history = st.session_state.chat_history[
                : st.session_state.question_chat_index
            ]
            st.session_state.ai_chat_history = st.session_state.ai_chat_history[
                : st.session_state.question_chat_index
            ]

            reset_question_answered_state()
            reset_question_generated_state()

        st.button(
            "Move to Next Question",
            type="primary",
            on_click=move_to_next_question,
            key="move_to_next_question",
        )
