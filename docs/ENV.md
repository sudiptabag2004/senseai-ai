# Environment Variables

### OPENAI_API_KEY
The API key for the OpenAI API.

### GOOGLE_CLIENT_ID
The client ID for the Google OAuth2.0 client.

## Deployment-Only Variables

### S3_BUCKET_NAME
The name of the S3 bucket used for storing files uploaded by users.

### S3_FOLDER_NAME
The name of the S3 folder within the S3 bucket. We use the same bucket for dev and prod but with different folder names.

### SENTRY_DSN (optional)
The Sentry DSN for the Sentry project.

### ENV (optional)
The environment the app is running in (staging/production).

### SLACK_USER_SIGNUP_WEBHOOK_URL (optional)
The Slack webhook URL for sending notifications to the user signup channel.

### SLACK_COURSE_CREATED_WEBHOOK_URL (optional)
The Slack webhook URL for sending notifications about new courses created.
