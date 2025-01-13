FROM python:3.13.1-slim-bookworm

RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    curl \
    wget \
    fontconfig \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    xfonts-75dpi \
    xfonts-base \
    ffmpeg \
    poppler-utils

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -
RUN apt-get install -y nodejs git

# Install libssl1.1
RUN wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb
RUN dpkg -i libssl1.1_1.1.1f-1ubuntu2_amd64.deb

# Install wkhtmltopdf
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.bullseye_amd64.deb \
    && dpkg -i wkhtmltox_0.12.6.1-2.bullseye_amd64.deb \
    && apt-get install -f \
    && rm wkhtmltox_0.12.6.1-2.bullseye_amd64.deb

# Verify wkhtmltopdf installation
RUN wkhtmltopdf --version

COPY streamlit-1.41.0-py2.py3-none-any.whl ./

# Copy requirements.txt to the container
COPY requirements.txt ./

# Install app dependencies
RUN pip install -r requirements.txt

COPY src /src

COPY src/.streamlit/config.prod.toml /src/.streamlit/config.toml

# Remove the /src/lib/.env and .env.aws file if it exists
RUN test -f /src/lib/.env && rm -f /src/lib/.env || true
RUN test -f /src/lib/.env.aws && rm -f /src/lib/.env.aws || true

# Expose the port on which your FastAPI app listens
EXPOSE 8001

# Only expose one port where everything is hosted
EXPOSE 8501

ARG APP_URL

ARG S3_BUCKET_NAME

ARG S3_FOLDER_NAME

ARG ENV

ARG OPENAI_API_KEY_ENCRYPTION_KEY

COPY src/.streamlit/secrets.${ENV}.toml /src/.streamlit/secrets.toml

RUN test -f /src/.streamlit/secrets.dev.toml && rm -f /src/.streamlit/secrets.dev.toml || true
RUN test -f /src/.streamlit/secrets.prod.toml && rm -f /src/.streamlit/secrets.prod.toml || true

RUN printf "APP_URL=$APP_URL\nS3_BUCKET_NAME=$S3_BUCKET_NAME\nS3_FOLDER_NAME=$S3_FOLDER_NAME\nOPENAI_API_KEY_ENCRYPTION_KEY=$OPENAI_API_KEY_ENCRYPTION_KEY" >> /src/lib/.env

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*