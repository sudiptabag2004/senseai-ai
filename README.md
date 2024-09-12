# SensAI - A Socratic AI Tutor

## Local Setup

- Install `virtualenv`
- Create a new virtual environment (choose Python3.8+)
  ```
  virtualenv -p python3.8 venv
  ```
- Activate the virtual environment
  ```
  source venv/bin/activate
  ```
- Install packages
  ```
  pip install -r app/requirements.txt
  ```
- Copy `src/lib/.env.example` to `src/lib/.env` and set the OpenAI credentials.

### Running the app locally

```
cd demo; streamlit run app.py
```

The app will be hosted on http://localhost:8501.

### Running the API locally

```
cd app; uvicorn main:app --reload --port 8001
```

The app will be hosted on http://localhost:8001.
The docs will be available on http://localhost:8001/docs


## Deployment
Use the `Dockerfile` provided to build a docker image and deploy the image to whatever infra makes sense for you. We use an EC2 instance for doing so and you can refer to the `.gitlab-ci.yml` and `docker-compose.ai.demo.yml` files to understand how we do Continuous Deployment (CD).


## Overview

- `app`: this folder contains the main AI logic for assessments and the FastAPI server
- `demo`: this folder contains various `streamlit` demos - for english, programming assessment and generating chapters + questions from a video (in the branch `content`). 
