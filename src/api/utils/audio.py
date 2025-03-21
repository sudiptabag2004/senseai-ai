import base64
import io
import tempfile
from openai import OpenAI
from api.settings import settings


async def transcribe_audio(audio_data: str) -> str:
    """
    Transcribe audio data using OpenAI's Whisper model

    Args:
        audio_data: Base64 encoded audio data

    Returns:
        Transcribed text
    """
    try:
        # Decode base64 audio data
        decoded_audio = base64.b64decode(audio_data)

        # Create a temporary file to store the audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
            temp_file.write(decoded_audio)
            temp_file.flush()

            # Initialize OpenAI client
            client = OpenAI(api_key=settings.openai_api_key)

            # Transcribe the audio using Whisper
            with open(temp_file.name, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1", file=audio_file
                )

            return transcription.text

    except Exception as e:
        # Log the error and raise it
        raise Exception(f"Error transcribing audio: {str(e)}")
