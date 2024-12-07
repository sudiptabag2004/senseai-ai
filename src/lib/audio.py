import base64
import streamlit as st


def validate_audio_input(audio_input) -> bool:
    file_size = audio_input.size  # Size in bytes
    max_size = 20 * 1024 * 1024  # 10MB in bytes

    if file_size > max_size:
        st.error(
            f"File size ({file_size/1024/1024:.1f}MB) exceeds maximum allowed size (20MB)"
        )
        return False

    return True


def prepare_audio_input_for_ai(audio_data: bytes):
    return base64.b64encode(audio_data).decode("utf-8")
