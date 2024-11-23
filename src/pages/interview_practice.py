import streamlit as st
import os
import base64
from typing import List

st.set_page_config(page_title="Interview Practice | SensAI", layout="wide")

from openai import OpenAI
from dotenv import load_dotenv
import instructor
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
import pandas as pd

from auth import redirect_if_not_logged_in
from lib.ui import display_waiting_indicator
from lib.llm import logger, get_formatted_history
from lib.init import init_env_vars
from components.buttons import back_to_home_button
from components.selectors import select_role, get_selected_role

# from streamlit_mic_recorder import mic_recorder
from audiorecorder import audiorecorder


init_env_vars()

redirect_if_not_logged_in(key="id")

questions = [
    "Tell me about yourself",
    "Why do you want to join our company?",
    "What are you short term and long term goals?",
    "Why did you apply for this role?",
    "Tell us your strengths and weakness",
    "Why do you have a career gap?",
    "Do you have any questions for us?",
    "How do you deal with criticism/ constructive feedback? Think of real world examples.",
    "How do you deal with challenges? Think of real world examples.",
    "Why should a company hire you?",
    "What are your major achievements?",
]

if "interview_started" not in st.session_state:
    st.session_state["interview_started"] = False

back_to_home_button()

with st.expander("Learn more"):
    st.warning(
        "This is still a work in progress. Please share any feedback that you might have!"
    )
    st.subheader("Goal")
    st.markdown(
        "You can improve your interviewing skills by getting feedback on your responses to standard interview questions."
    )
    st.subheader("How it works")
    st.markdown(
        "1. Enter the name of the role you want to submit your CV for and press `Enter`.\n\n2. Select one of the standard interview questions and press `Start Interview`.\n\n3. Send your audio response as you would if the question was asked in an interview.\n\n4. SensAI will analyze your response and give feedback on how you can improve it.\n\n5. Reload the page and practice your answer again."
    )

cols = st.columns([3, 3, 1])
with cols[0]:
    select_role()

selected_role = get_selected_role()

if not selected_role:
    st.stop()

with cols[1]:
    selected_question = st.selectbox(
        "Select question to interview you on",
        questions,
        index=None,
        disabled=st.session_state["interview_started"],
    )

if not selected_question:
    st.stop()


if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0


def update_file_uploader_key():
    st.session_state.file_uploader_key += 1


def refresh_audio_data():
    st.session_state.audio_data = None


if "audio_data" not in st.session_state:
    refresh_audio_data()


def start_interview():
    st.session_state["interview_started"] = True


def reset_interview():
    st.session_state["interview_started"] = False
    refresh_audio_data()


def reset_ai_running():
    st.session_state["is_ai_running"] = False


def toggle_ai_running():
    st.session_state["is_ai_running"] = not st.session_state["is_ai_running"]


if "is_ai_running" not in st.session_state:
    reset_ai_running()


if "ai_response_rows" not in st.session_state:
    st.session_state.ai_response_rows = []

with cols[-1]:
    st.container(height=10, border=False)
    if not st.session_state["interview_started"]:
        st.button("Start Interview", on_click=start_interview)
        st.stop()
    else:
        st.button(
            "End Interview",
            on_click=reset_interview,
            disabled=st.session_state.is_ai_running,
        )


def get_wav_data_from_file_upload(audio_file):
    with st.spinner("Processing audio..."):
        import io
        from pydub import AudioSegment

        audio_bytes = audio_file.read()
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_data = wav_buffer.getvalue()

    return wav_data


# def get_wav_data_from_audio_input(audio_value):
#     return audio_value.read()


def show_ai_report():
    df = pd.DataFrame(
        st.session_state.ai_response_rows, columns=["Category", "Feedback"]
    )

    st.markdown(
        df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )


def give_feedback_on_audio_input():
    encoded_string = base64.b64encode(st.session_state.audio_data).decode("utf-8")

    container = st.empty()

    with container:
        display_waiting_indicator()

    model = "gpt-4o-audio-preview-2024-10-01"

    class Feedback(BaseModel):
        topic: str = Field(description="topic of the feedback")
        feedback: str = Field(description="feedback for this topic")

    class Output(BaseModel):
        feedback: List[Feedback] = Field(
            description="Holistic feedback on the mentee's response"
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    # examples = [
    #     """Your response is quite good, but there are a few minor grammatical errors. Here\'s a revised version:\n\n"In recent times, I have managed my stress by involving myself in reading books and listening to melodies. It has helped me to overcome my frustration. It has opened new ways and given a new pathway to my life."\n\nFeedback:\n1. Use "have managed" instead of "managed" to indicate an ongoing action.\n2. Use "melodies" instead of "melody" to refer to listening to music in general.\n3. Use "has helped" instead of "helped" for consistency in tense.\n4. Use "has opened" and "given" for consistency in tense.\n\nOverall, your answer is clear and well-structured. Keep up the good work!""",
    #     """Your response is mostly correct, but there are a couple of minor improvements you could make for clarity and grammatical accuracy:\n\n1. "I should have done the JAM event in a different manner." - This sentence is correct, but you might want to specify what "JAM" stands for if it\'s not commonly known to your audience.\n\n2. "I did a good job. But I feel that I would have done it better." - The word "would" in the second sentence is slightly off in this context. It would be more accurate to say, "I feel that I could have done it better."\n\nHere\'s a revised version: "I should have done the JAM event in a different manner. I did a good job, but I feel that I could have done it better."\n\nOverall, your response is clear and well-structured. Keep up the good work!""",
    #     """Your answer is mostly clear, but there are a few minor grammatical errors and areas for improvement:\n\n1. "the hardship of boarding my hometown bus during this Thursday" - It would be clearer to say "the hardship of boarding the bus to my hometown this Thursday."\n\n2. "Although it was challenging, it was fun too." - This sentence is correct, but you could add a comma after "Moreover" in the next sentence for better readability.\n\n3. "Moreover it became a short break after tedious work hours." - It would be clearer to say "Moreover, it provided a short break after tedious work hours."\n\nHere\'s a revised version of your response:\n\n"I faced the hardship of boarding the bus to my hometown this Thursday. Although it was challenging, it was fun too. Moreover, it provided a short break after tedious work hours."\n\nGreat effort! Keep practicing, and you\'ll continue to improve.""",
    # ]

    # examples_for_prompt = "\n\n".join(
    #     [
    #         f"Feedback {index + 1}:\n```\n{example}\n```"
    #         for index, example in enumerate(examples)
    #     ]
    # )
    # \n\nHere are a few examples of desirable feedback:\n{examples_for_prompt}\n\n=========

    system_prompt = f"""You are an expert, helpful, encouraging and empathetic coach who is helping your mentee improve their interviewing skills for the role of {selected_role}.\n\nYou will be given an interview question and the conversation history between you and the mentee.\n\nYou need to give feedback on the mentee's response on what part of their answer stood out, what pieces were missing, what they did well, and what could they have done differently, in light of best practices for interviews, including tense consistency, clarity, precision, sentence structure, clarity of speech and confidence.\n\nImportant Instructions:\n- Make sure to categorize the different aspects of feedback into individual topics so that it is easy to process for the mentee.\n- You must be very specific about exactly what part of the mentee's response you are suggesting any improvement for by quoting directly from their response along with a clear example of how it could be improved. The example for the improvement must be given as if the mentee had said it themselves.\n\nAvoid demotivating the mentee. Only provide critique where it is clearly necessary and praise them for the parts of their response that are good.\n- Some mandatory topics for the feedback are: tense consistency, clarity, precision, sentence structure, clarity of speech and confidence. Add more topics as you deem fit.\n- Give any feedback as needed on how their response to the question can be made more suited to the role of a {selected_role}.\n\n{format_instructions}"""

    client = instructor.from_openai(OpenAI())

    ai_chat_history = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {"role": "user", "content": f"Question: ```{selected_question}```"},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {"data": encoded_string, "format": "wav"},
                },
            ],
        },
    ]
    stream = client.chat.completions.create_partial(
        model=model,
        messages=ai_chat_history,
        response_model=Output,
        max_completion_tokens=2048,
        stream=True,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=True,
    )

    # TODO: what about if student just wants to ask something instead of answering prompt, using text?
    # TODO: for just text, we need to add a new prompt

    rows = []
    for val in stream:
        if not val.feedback:
            continue

        for index, topicwise_feedback in enumerate(val.feedback):
            if not topicwise_feedback.topic or not topicwise_feedback.feedback:
                continue

            if (
                rows
                and len(rows) > index
                and rows[index][0] == topicwise_feedback.topic
            ):
                rows[index][1] = topicwise_feedback.feedback
            else:
                rows.append([topicwise_feedback.topic, topicwise_feedback.feedback])

        st.session_state.ai_response_rows = rows
        with container:
            show_ai_report()

    logger.info(get_formatted_history(ai_chat_history))
    toggle_ai_running()
    st.rerun()


def reset_params():
    del st.session_state.ai_response_rows
    del st.session_state.audio_data


# def audio_recording_callback():
#     if not st.session_state.my_recorder_output:
#         return

#     st.session_state.audio_data = st.session_state.my_recorder_output["bytes"]
#     st.rerun()


if st.session_state.audio_data:
    user_input_col, _, ai_report_col = st.columns([1, 0.1, 1.5])
    with user_input_col:
        cols = st.columns([3, 1])
        with cols[0]:
            st.subheader("Your response")
            st.audio(st.session_state.audio_data)

        with cols[1]:
            st.container(height=40, border=False)
            st.download_button(
                "Download",
                data=st.session_state.audio_data,
                file_name="interview_response.wav",
                mime="audio/wav",
            )

        st.button(
            "Delete response",
            on_click=reset_params,
            type="primary",
            disabled=st.session_state.is_ai_running,
        )

    with ai_report_col:
        st.container(height=20, border=False)

        if st.session_state.ai_response_rows:
            show_ai_report()
        else:
            give_feedback_on_audio_input()
else:
    input_type = st.radio(
        "How would you like to respond?", ["Record my answer", "Upload my answer"]
    )
    is_recording = input_type == "Record my answer"

    if is_recording:
        if "localhost" in os.environ["APP_URL"]:
            st.info(
                f"To record in browser (only required for testing locally):\n1. type the url `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in your browser\n2. Enter {os.environ['APP_URL']} in the textarea\n3. Choose `Enabled` and relaunch the browser"
            )
        # audio_value = st.audio_input(
        #     "Record a voice message by pressing on the mic icon"
        # )

        # mic_recorder(
        #     start_prompt="Start recording",
        #     stop_prompt="Stop recording",
        #     just_once=False,
        #     use_container_width=False,
        #     format="wav",
        #     callback=audio_recording_callback,
        #     args=(),
        #     kwargs={},
        #     key="my_recorder",
        # )
        audio_value = audiorecorder(
            "",
            "",
            pause_prompt="",
            custom_style={"color": "black"},
            start_style={},
            pause_style={},
            stop_style={},
            show_visualizer=True,
            key=None,
        )

    else:
        audio_value = st.file_uploader(
            "Upload your answer (audio)",
            key=f"file_uploader_{st.session_state.file_uploader_key}",
            type=["wav", "mp3", "mov"],
        )

    if audio_value:
        if is_recording:
            st.session_state.audio_data = audio_value.export(format="wav").read()
        else:
            st.session_state.audio_data = get_wav_data_from_file_upload(audio_value)

        update_file_uploader_key()
        toggle_ai_running()
        st.rerun()
