import base64
import wave
import io
import streamlit as st


def validate_audio_input(audio_input) -> bool:
    # Check audio duration
    audio_bytes = io.BytesIO(audio_input.read())
    try:
        with wave.open(audio_bytes) as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = frames / float(rate)

            if duration < 1.0:
                return "Audio recording must be at least 1 second long"

        # Reset file pointer for subsequent reads
        audio_input.seek(0)
    except Exception:
        return "Invalid audio file format"

    file_size = audio_input.size  # Size in bytes
    max_size = 20 * 1024 * 1024  # 10MB in bytes

    if file_size > max_size:
        return f"File size ({file_size/1024/1024:.1f}MB) exceeds maximum allowed size (20MB)"


def prepare_audio_input_for_ai(audio_data: bytes):
    return base64.b64encode(audio_data).decode("utf-8")
