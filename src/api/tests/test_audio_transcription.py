import pytest
import base64
import os
from unittest.mock import patch, MagicMock
from api.utils.audio import transcribe_audio


@pytest.mark.asyncio
async def test_transcribe_audio():
    # Create a mock audio data (base64 encoded string)
    mock_audio_data = base64.b64encode(b"mock audio data").decode("utf-8")

    # Create a mock transcription response
    mock_transcription = MagicMock()
    mock_transcription.text = "This is the transcribed text"

    # Mock the OpenAI client and its response
    with patch("api.utils.audio.OpenAI") as mock_openai:
        # Set up the mock to return our mock transcription
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = mock_transcription

        # Call the function with our mock data
        result = await transcribe_audio(mock_audio_data)

        # Assert the result is what we expect
        assert result == "This is the transcribed text"

        # Assert the OpenAI client was called with the correct parameters
        mock_client.audio.transcriptions.create.assert_called_once()


@pytest.mark.asyncio
async def test_transcribe_audio_error():
    # Create a mock audio data (base64 encoded string)
    mock_audio_data = base64.b64encode(b"mock audio data").decode("utf-8")

    # Mock the OpenAI client to raise an exception
    with patch("api.utils.audio.OpenAI") as mock_openai:
        # Set up the mock to raise an exception
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = Exception("Test error")

        # Assert that the function raises an exception
        with pytest.raises(Exception) as excinfo:
            await transcribe_audio(mock_audio_data)

        # Assert the exception message contains our error
        assert "Test error" in str(excinfo.value)
