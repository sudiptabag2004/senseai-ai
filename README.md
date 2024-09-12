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
cd src; streamlit run home.py
```

The app will be hosted on http://localhost:8501.

### Running the API locally

```
cd src; uvicorn api:app --reload --port 8001
```

The app will be hosted on http://localhost:8001.
The docs will be available on http://localhost:8001/docs


## Deployment
Use the `Dockerfile` provided to build a docker image and deploy the image to whatever infra makes sense for you. We use an EC2 instance and you can refer to the `.gitlab-ci.yml` and `docker-compose.ai.demo.yml` files to understand how we do Continuous Deployment (CD).


## Philosophy
- You will see a lot of best practices being violated. For e.g. anyone can log in as anyone just by providing their email address, there is no security on the API exposed, anyone can make the API call and get the entire chat history.
- You will also see things being done very simply. For most of the tasks where LLMs are used, a single LLM call is made with a simple system prompt. We are not using any fine-tuned model or any open-source model as well. We are simply a wrapper on OpenAI. 
- The reason for this is that the user (a.k.a. the learners and the teachers) don't care about the tech behind the product. The only thing that matters to them is whether it works. Too often we get hung up on applying the most fancy technique and we don't pay attention to the reason the product exists - to solve a real-world problem.
- When a team is really small, what we focus on is really important. Since we are working on this on our own time, we have to ensure that we get the biggest buck out of it. This means that we will deprioritise many things that seem important but are really not, for the moment. For example, what matters to us right now is building features, fixing bugs and collecting rapid feedback to make sure we have a product that works. At this time, no one is going to try to hack into our system to figure out the IP address of our hosted instance and query it to fetch the chat history of our users. Even if someone ends up doing so, the chat history does not contain any PII and non-risky.
- If you feel strongly about any best practice, please feel free to create a Pull Request! :)


## Overview

The app is built using `streamlit`. We use `streamlit-cookies-manager` for storing a user's credentials and keeping them logged in.

- `app`: this folder contains the main AI logic for assessments and the FastAPI server
- `demo`: this folder contains various `streamlit` demos - for english, programming assessment and generating chapters + questions from a video (in the branch `content`). 