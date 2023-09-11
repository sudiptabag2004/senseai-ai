# Use an official Python runtime as the base image
FROM python:3.8.17-slim-bookworm

RUN apt-get update && apt-get install -y gcc python3-dev

# Copy requirements.txt to the container
COPY requirements.txt /workspace

WORKDIR /workspace

# Install app dependencies
RUN pip install -r requirements.txt

# Copy the rest of the source code to the container
COPY . /workspace/

# update langchain library files to fix issues with caching + streaming
# for chat models
WORKDIR /workspace

RUN bash update_langchain.sh

# Expose the port on which your FastAPI app listens
EXPOSE 8001

# Expose the port on which your Streamlit app listens
EXPOSE 8501
