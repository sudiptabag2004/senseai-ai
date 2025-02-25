## Environment Variables

## Frontend
- `APP_URL`: The URL of the app. E.g. when running locally on port 8501, this should be http://localhost:8501
- `S3_BUCKET_NAME`: The name of the S3 bucket used for storing files uploaded by users.
- `S3_FOLDER_NAME`: The name of the S3 folder within the S3 bucket. We use the same bucket for dev and prod but with different folder names.
- `OPENAI_API_KEY_ENCRYPTION_KEY`: We store the API keys for each organization in the database encrypted with this key. Generate a symmetric encryption key and store it in this environment variable.
- `BACKEND_URL`: The URL of the backend API. E.g. when running locally on port 8001, this should be http://localhost:8001

## Backend

- `OPENAI_API_KEY_ENCRYPTION_KEY`: Use the same value as the `OPENAI_API_KEY_ENCRYPTION_KEY` in the frontend section.
