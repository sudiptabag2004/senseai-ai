import streamlit as st

st.set_page_config(page_title="Mock Interview | SensAI", layout="wide")

from typing import Tuple, List, Optional, Literal
import pypdf
from streamlit_pdf_viewer import pdf_viewer

from streamlit.runtime.uploaded_file_manager import UploadedFile

from components.buttons import back_to_home_button
from auth import redirect_if_not_logged_in

redirect_if_not_logged_in(key="id")
back_to_home_button()

with st.expander("Learn more"):
    st.warning(
        "This is still a work in progress. Please share any feedback that you might have!"
    )
    st.subheader("Goal")
    st.markdown(
        "You can refine your CV by getting feedback regarding appearance, clarity, communication, grammar, link verification for linked emails and the linked phone number, etc. on your current CV and any updated versions of it."
    )
    st.subheader("How it works")
    st.markdown(
        "1. Enter the name of the role you want to submit your CV for and press `Enter`.\n\n2. Upload your CV.\n\n3. SensAI will analyze your CV and give you feedback on multiple parameters of your CV as explained above.\n\n4. Incorporate the feedback into your CV and upload the updated version of your CV to get feedback on it again."
    )


if "file_uploader_key" not in st.session_state:
    st.session_state.file_uploader_key = 0

if "cv_data" not in st.session_state:
    st.session_state.cv_data = None

if "ai_response_rows" not in st.session_state:
    st.session_state.ai_response_rows = []

if "invalid_links" not in st.session_state:
    st.session_state.invalid_links = []

role_col, cv_upload_col = st.columns([2, 1])

with role_col:
    st.text_input(
        "Name of the role you want to apply for (e.g. Software Developer)",
        disabled=st.session_state.cv_data is not None,
        key="selected_role",
    )

cols = st.columns([1, 0.1, 2])

cv_container = cols[0].container()
ai_report_container = cols[2].container()
links_container = cols[2].empty()


def update_file_uploader_key():
    st.session_state.file_uploader_key += 1


def set_cv(cv: UploadedFile):
    st.session_state.cv_data = cv
    update_file_uploader_key()


def reset_ai_running():
    st.session_state["is_ai_running"] = False


def toggle_ai_running():
    st.session_state["is_ai_running"] = not st.session_state["is_ai_running"]


if "is_ai_running" not in st.session_state:
    reset_ai_running()


def validate_url(url: str) -> Tuple[bool, str]:
    """
    Validates if a URL is accessible.
    Returns a tuple of (is_valid: bool, error_message: str)
    """
    import requests
    from urllib.parse import urlparse

    try:
        # Parse URL to check if it's well-formed
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "Invalid URL format"

        # Try to make a HEAD request with a timeout
        response = requests.head(url, timeout=5, allow_redirects=True)
        response.raise_for_status()
        return True, "Valid"
    except requests.exceptions.Timeout:
        return False, "Timeout error"
    except requests.exceptions.SSLError:
        return False, "SSL certificate error"
    except requests.exceptions.ConnectionError:
        return False, "Connection error"
    except requests.exceptions.RequestException as e:
        return False, f"Error: {str(e)}"


def get_invalid_links(links: List[str]) -> List[Tuple[str, str]]:
    invalid_links = []

    for link in links:
        is_valid, error_msg = validate_url(link)
        if is_valid:
            continue

        invalid_links.append((link, error_msg))

    return invalid_links


def get_email_links(links: List[str]) -> List[str]:
    return [link for link in links if "mailto" in link]


def get_phone_number_links(links: List[str]) -> List[str]:
    return [link for link in links if "tel" in link]


def get_email_from_email_links(email_links: List[str]) -> Optional[str]:
    for link in email_links:
        if "mailto" in link:
            return link.split(":")[1]

    return None


def get_phone_number_from_phone_links(phone_links: List[str]) -> Optional[str]:
    for link in phone_links:
        if "tel" in link:
            return link.split(":")[1]

    return None


def show_ai_report(container: st.container = None):
    import pandas as pd

    df = pd.DataFrame(
        st.session_state.ai_response_rows, columns=["Category", "Feedback"]
    )

    display_container = container if container else ai_report_container
    with display_container:
        st.markdown(
            df.to_html(escape=False, index=False),
            unsafe_allow_html=True,
        )

    if display_container == ai_report_container:
        if st.session_state.invalid_links:
            with links_container.expander("Invalid Links"):
                for link, error in st.session_state.invalid_links:
                    st.markdown(f"- `{link}`: {error.replace(link, '')}")


def generate_cv_report(pdf: pypdf.PdfReader):
    import tempfile
    import json
    from openai import OpenAI
    from dotenv import load_dotenv
    import instructor
    from pydantic import BaseModel, Field
    from langchain_core.output_parsers import PydanticOutputParser
    from lib.init import init_env_vars
    from lib.config import PDF_PAGE_DIMS
    from lib.ui import display_waiting_indicator
    from lib.pdf import get_raw_images_from_pdf, get_links_from_pdf
    from lib.image import get_base64_images
    from lib.llm import get_formatted_history, logger

    init_env_vars()
    toggle_ai_running()

    # Create a temporary file to store the PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(st.session_state.cv_data.getvalue())
        temp_pdf.flush()
        pdf_path = temp_pdf.name
        raw_images = get_raw_images_from_pdf(pdf_path, PDF_PAGE_DIMS, max_pages=2)
        base64_images = get_base64_images(raw_images)

    container = st.empty()

    with container:
        display_waiting_indicator()

    model = "gpt-4o-2024-08-06"

    class Feedback(BaseModel):
        topic: str = Field(description="topic of the feedback")
        feedback: str = Field(description="feedback for this topic")

    class Output(BaseModel):
        feedback: List[Feedback] = Field(
            description="Holistic feedback on the student's response"
        )
        email: Optional[str] = Field(
            description="email of the student; null if not provided", default=None
        )
        phone_number: Optional[str] = Field(
            description="phone number of the student; null if not provided",
            default=None,
        )

    parser = PydanticOutputParser(pydantic_object=Output)
    format_instructions = parser.get_format_instructions()

    system_prompt = f"""f"You are an expert, helpful, encouraging and empathetic {st.session_state.selected_role} coach who is helping your mentee improve their CV so that they can be shortlisted for interviews.\n\nYou will be given the images of their CV and the conversation history between you and the mentee.\n\nYou need to give feedback on the mentee's CV. Use the following structured guidelines to evaluate and provide actionable feedback:\n\n### 1. **Appearance and Styling**\n- Check if the resume is clean and easy to read. \n- The introduction should include:\n  - LinkedIn and GitHub links\n  - Email ID (optional but acceptable)\n- Ensure the alignment and formatting are professional, with all sections consistently organized.  \n- Confirm that the resume does **not** include a photo.\n- Make sure it contains:\n  - Name\n  - Phone number\n  - Email ID\n  - Basic address in a simple format (e.g., "Anna Nagar, Chennai, Tamil Nadu")\n\n### 2. **Education**\n- Verify that educational details are clearly presented:\n  - Name of the institution\n  - Year of graduation or duration of the course\n  - Subjects or areas of study relevant to the field\n\n### 3. **Professional Development**\n- Check for a section that highlights professional development. Ensure details follow this template:  \n  *“Received fellowship in <Web Development, Data Science, DevOps> as part of Hyperverge Academy from <2023 August till 2024 March>. The program included extensive training in technical skills (such as <SQL, Python, Excel>) as well as power skills (such as public speaking, communication, etc.).”*\n\n### 4. **Introduction or Personal Summary**\n- Ensure the section includes relevant keywords for the job role (e.g., "front-end," "back-end," "Data Science").\n- Assess whether the candidate explains their choice of field in simple, compelling terms.\n- Flag and provide feedback on sentences that are too generic or complex. Suggest using concise, clear sentences. Example: Instead of “I am passionate about tech and always eager to learn,” recommend “I specialize in building front-end applications because I enjoy creating intuitive user experiences.”\n\n### 5. **Projects**\n- Projects should be well-documented with:\n  - Clear feature descriptions\n  - Purpose of the project\n  - Technologies used\n- Avoid generic statements. For instance, replace “Worked on a project” with “Developed a real-time chat app using Python and Streamlit, integrated with an SQLite database to store chat history.”\n\n### 6. **Order of Events**\n- Ensure the CV follows this order:\n  1. **Professional Development** (with highlighted projects)\n  2. **Education**\n  3. **Achievements**\n  4. **Certifications**\n- Check that projects are prominently emphasized.\n\n### 7. **Grammar and English**\n- Proofread the entire document for grammar, spelling errors, and sentence structure.\n- Recommend using tools like Grammarly or Google Docs for improvements.\n- Ensure the language is polished, free of jargon, and professional.\n\n### 8. **Links and Functionality**\n- Verify that all hyperlinks (e.g., LinkedIn, GitHub, project repositories) are functional and correctly linked.\n\n### 9. **Certifications**\n- Confirm that certifications are relevant to the desired job role.\n- Acceptable certifications can be from Udemy, Coursera, HackerRank, or other reputable sources.\n- Ensure certifications add value to the candidate\'s skill set.\n\n### 10. **Feedback and Suggestions**\n- Provide concise, actionable feedback on:\n  - Complex or generic content\n  - Missing or incorrectly formatted sections\n  - Suggestions for clearer and more compelling language\n- Highlight any additional areas for improvement, ensuring the resume is job-specific and polished for the intended role.\n\nUse this structured approach to evaluate the CV and provide a detailed assessment to enhance the student\'s job readiness.\n\nImportant Instructions:\n- Make sure to categorize the different aspects of feedback into the individual topics given above so that it is easy to process for the mentee.\n- You must be very specific about exactly what part of the mentee's response you are suggesting any improvement for by quoting directly from their CV along with a clear example of how it could be improved. The example for the improvement must be given as if the mentee had written it themselves.\n\nAvoid demotivating the mentee. Only provide critique where it is clearly necessary and praise them for the parts of their CV that are good.\n- Some mandatory topics for the feedback are: Appearance and Styling, Content, Order of Events, Grammar and English, Certifications, Links. Add more topics as you deem fit.\n\n{format_instructions}"""

    client = instructor.from_openai(OpenAI())

    ai_chat_history = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image}",
                    },
                }
                for image in base64_images
            ],
        },
    ]
    stream = client.chat.completions.create_partial(
        model=model,
        messages=ai_chat_history,
        response_model=Output,
        stream=True,
        max_completion_tokens=2048,
        temperature=0,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        store=True,
    )

    rows = []
    email_in_cv = None
    phone_in_cv = None
    for val in stream:
        if not val.feedback and not val.email and not val.phone_number:
            continue

        if val.email and email_in_cv is None:
            email_in_cv = val.email
            continue

        if val.phone_number and phone_in_cv is None:
            phone_in_cv = val.phone_number
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
        show_ai_report(container=container)

    with st.spinner("Checking links"):
        links = get_links_from_pdf(pdf)

        email_links = get_email_links(links)
        phone_links = get_phone_number_links(links)
        external_links = [
            link for link in links if link not in email_links + phone_links
        ]

        email_in_link = get_email_from_email_links(email_links)
        phone_in_link = get_phone_number_from_phone_links(phone_links)
        invalid_links = get_invalid_links(external_links)

        link_feedbacks = []
        if invalid_links:
            link_feedbacks.append(
                "⚠️ A few links in your CV may be invalid or inaccessible"
            )
        else:
            link_feedbacks.append("✅ All links in your CV are valid and accessible")

        if email_in_link and email_in_cv:
            if email_in_link == email_in_cv:
                link_feedbacks.append(f"✅ Email linked matches the email in your CV")
            else:
                link_feedbacks.append(
                    f"❌ Email linked ({email_in_link}) does not match the email in your CV ({email_in_cv})"
                )

        if phone_in_link and phone_in_cv:
            if phone_in_link == phone_in_cv:
                link_feedbacks.append(
                    f"✅ Phone number linked matches the phone number in your CV"
                )
            else:
                link_feedbacks.append(
                    f"❌ Phone number linked ({phone_in_link}) does not match the phone number in your CV ({phone_in_cv})"
                )

    row_with_link_feedback = [
        index for index, row in enumerate(rows) if row[0] == "Links"
    ]
    if row_with_link_feedback:
        link_feedbacks = [rows[row_with_link_feedback[0]][1]] + link_feedbacks
        rows[row_with_link_feedback[0]][1] = "<br>".join(link_feedbacks)
    else:
        rows.append(["Links", "<br>".join(link_feedbacks)])

    st.session_state.ai_response_rows = rows
    st.session_state.invalid_links = invalid_links

    container.empty()
    show_ai_report()

    toggle_ai_running()


def show_uploaded_cv():
    with cv_container:
        pdf_viewer(st.session_state.cv_data.getvalue(), height=600, render_text=True)


def run_cv_review():
    pdf = pypdf.PdfReader(st.session_state.cv_data)
    num_pages = len(pdf.pages)

    if num_pages > 2:
        st.error("Please upload a PDF with 2 pages or less!")
        st.stop()

    with ai_report_container:
        generate_cv_report(pdf)


def reset_params():
    del st.session_state.ai_response_rows
    del st.session_state.invalid_links
    del st.session_state.cv_data
    cv_container.empty()
    ai_report_container.empty()
    links_container.empty()


def show_cv_uploader():
    key = f"cv_{st.session_state.file_uploader_key}"
    description = "Upload your CV (PDF)"

    if uploaded_file := cv_upload_col.file_uploader(
        description,
        key=key,
        type="pdf",
    ):
        set_cv(uploaded_file)
        st.rerun()


if not st.session_state.cv_data:
    key = f"cv_{st.session_state.file_uploader_key}"

    if st.session_state.selected_role:
        show_cv_uploader()

else:
    show_uploaded_cv()

    if st.session_state.ai_response_rows:
        show_ai_report()
    else:
        run_cv_review()

    cv_upload_col.container(height=10, border=False)
    cv_upload_col.button("Delete CV", on_click=reset_params, type="primary")
