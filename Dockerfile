FROM python:3.9.19-slim-bookworm

RUN apt-get update && apt-get install -y gcc python3-dev

# Copy requirements.txt to the container
COPY requirements.txt ./

# Install app dependencies
RUN pip install -r requirements.txt

# Copy the rest of the app source code to the container
# COPY app /app

# Copy the demo source code to the container
COPY demo /demo

# Expose the port on which your FastAPI app listens
EXPOSE 8001

# Only expose one port where everything is hosted
EXPOSE 8501

# EXPOSE 8502

# EXPOSE 8503

ARG OPENAI_API_KEY

ARG OPENAI_ORG_ID

RUN echo $OPENAI_API_KEY

RUN printf "OPENAI_API_KEY=$OPENAI_API_KEY\nOPENAI_ORG_ID=$OPENAI_ORG_ID" >> /demo/lib/.env

# COPY langchain /langchain
# RUN mkdir /appdata

# COPY langchain /langchain

# COPY update_langchain.sh ./

# RUN bash update_langchain.sh