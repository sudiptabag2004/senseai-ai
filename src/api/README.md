# SensAI API

This directory contains the FastAPI-based backend API for SensAI.

## Features

### Audio Chat Support

The API now supports audio input for chat conversations. Users can send audio recordings which will be automatically transcribed and processed as text responses.

#### How to use audio input:

1. Send a POST request to `/ai/chat` endpoint with the following payload:

```json
{
  "user_response": "",  // Can be empty when using audio
  "question_id": 123,   // Required if not providing question
  "user_id": 456,       // Required with question_id
  "audio_data": "base64_encoded_audio_data"  // Base64 encoded WAV audio
}
```

2. The API will:
   - Transcribe the audio to text using OpenAI's Whisper model
   - Process the transcribed text as if it was a normal text user_response
   - Return the AI response as usual

3. Error handling:
   - If audio transcription fails, a 500 error will be returned with details
   - Audio should be in WAV format for best results

## API Endpoints

- `POST /ai/chat`: Get AI response for a question
  - Accepts both text and audio input
  
## Development

### Testing

Run tests with pytest:

```bash
pytest src/api/tests/
``` 