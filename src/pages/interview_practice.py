import streamlit as st
import os

st.set_page_config(page_title="Interview Practice | SensAI", layout="wide")

from auth import redirect_if_not_logged_in
from lib.ui import display_waiting_indicator
from lib.llm import logger, get_formatted_history
from components.buttons import back_to_home_button

redirect_if_not_logged_in(key="id")

questions = [
    "Tell me about yourself",
    "Why do you want to join our company?",
    "What are you short term and long term goals?",
    "Why did you apply for this role?",
    "Tell us your strengths and weakness",
    "Why do you have a career gap?",
    "Do you have any questions for us?",
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
    selected_role = st.text_input(
        "Enter the name of the role you want to interview for (e.g. Software Developer)",
        disabled=st.session_state["interview_started"],
    )

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


with cols[-1]:
    st.container(height=10, border=False)
    if not st.session_state["interview_started"]:
        st.button("Start Interview", on_click=start_interview)
        st.stop()
    else:
        st.button("End Interview", on_click=reset_interview)


def get_wave_data_from_file_upload(audio_file):
    with st.spinner("Processing audio..."):
        import io
        from pydub import AudioSegment

        audio_bytes = audio_file.read()
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
        wav_buffer = io.BytesIO()
        audio.export(wav_buffer, format="wav")
        wav_data = wav_buffer.getvalue()

    return wav_data


def get_wave_data_from_audio_input(audio_value):
    return audio_value.read()


def give_feedback_on_audio_input():
    import base64
    from typing import List
    from openai import OpenAI
    from dotenv import load_dotenv
    import instructor
    from pydantic import BaseModel, Field
    from langchain_core.output_parsers import PydanticOutputParser
    from lib.init import init_env_vars

    init_env_vars()

    encoded_string = base64.b64encode(st.session_state.audio_data).decode("utf-8")

    container = st.empty()

    with container:
        display_waiting_indicator()

    model = "gpt-4o-audio-preview"

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

    system_prompt = f"""f"You are an expert, helpful, encouraging and empathetic {selected_role} coach who is helping your mentee improve their interviewing skills.\n\nYou will be given an interview question and the conversation history between you and the mentee.\n\nYou need to give feedback on the mentee's response on what part of their answer stood out, what pieces were missing, what they did well, and what could they have done differently, in light of best practices for interviews, including tense consistency, clarity, precision, sentence structure, clarity of speech and confidence.\n\nImportant Instructions:\n- Make sure to categorize the different aspects of feedback into individual topics so that it is easy to process for the mentee.\n- You must be very specific about exactly what part of the mentee's response you are suggesting any improvement for by quoting directly from their response along with a clear example of how it could be improved. The example for the improvement must be given as if the mentee had said it themselves.\n\nAvoid demotivating the mentee. Only provide critique where it is clearly necessary and praise them for the parts of their response that are good.\n- Some mandatory topics for the feedback are: tense consistency, clarity, precision, sentence structure, clarity of speech and confidence. Add more topics as you deem fit.\n\n{format_instructions}"""

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

    ai_response = ""
    for val in stream:
        if not val.feedback:
            continue

        display_feedback = ""

        for topicwise_feedback in val.feedback:
            if not topicwise_feedback.topic or not topicwise_feedback.feedback:
                continue

            display_feedback += (
                f"**{topicwise_feedback.topic}**\n\n{topicwise_feedback.feedback}\n\n"
            )

        if not display_feedback:
            continue

        container.markdown(display_feedback)
        ai_response = val.feedback

    ai_chat_history.append({"role": "assistant", "content": ai_response})
    logger.info(get_formatted_history(ai_chat_history))

    update_file_uploader_key()


if st.session_state.audio_data:
    with st.chat_message("user"):
        st.audio(st.session_state.audio_data)

    with st.chat_message("assistant"):
        give_feedback_on_audio_input()
else:
    input_type = st.radio(
        "How would you like to respond?", ["Record my answer", "Upload my answer"]
    )
    is_recording = input_type == "Record my answer"
    with st.chat_message("user"):
        if is_recording:
            if "localhost" in os.environ["APP_URL"]:
                st.info(
                    f"To record in browser (only required for testing locally):\n1. type the url `chrome://flags/#unsafely-treat-insecure-origin-as-secure` in your browser\n2. Enter {os.environ['APP_URL']} in the textarea\n3. Choose `Enabled` and relaunch the browser"
                )
            audio_value = st.experimental_audio_input(
                "Record a voice message by pressing on the mic icon"
            )
        else:
            audio_value = st.file_uploader(
                "Upload your answer (audio)",
                key=f"file_uploader_{st.session_state.file_uploader_key}",
                type=["wav", "mp3", "mov"],
            )

    if audio_value:
        if is_recording:
            st.session_state.audio_data = get_wave_data_from_audio_input(audio_value)
        else:
            st.session_state.audio_data = get_wave_data_from_file_upload(audio_value)
        st.rerun()
