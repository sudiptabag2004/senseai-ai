# SensAI AI

## Overview

- `app`: this folder contains the main AI logic for assessments and the FastAPI server
- `demo`: this folder contains various `streamlit` demos - for english, programming assessment and generating chapters + questions from a video (in the branch `content`). 

## Setup

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
- Update environment variables inside `app/.env`.
- Update certain langchain files to accommodate fixes:
  ```
  bash update_langchain.sh
  ```
  The changes made are shown in the images inside the `langchain` dir.

## Running the API locally

```
cd app; uvicorn main:app --reload --port 8001
```

The app will be hosted on http://localhost:8001.
The docs will be available on http://localhost:8001/docs

## Running the demo app locally

```
cd demo; streamlit run app.py
```

The app will be hosted on http://localhost:8501.


