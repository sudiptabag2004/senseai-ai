# Use an official Python runtime as the base image
FROM python:3.8.17-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the container
COPY app/requirements.txt ./

# Install app dependencies
RUN pip install -r requirements.txt

# Copy the rest of the app source code to the container
COPY app/. .

# Expose the port on which your FastAPI app listens
EXPOSE 8001

# Start the Express app
CMD ["uvicorn", "main:app", "--reload", " --port", "8001"]
