# SensAI - A Socratic AI Tutor

We are building an AI tutor to help students learn and assist teachers in creating lessons, evaluating student responses and keeping their students motivated.
We are HyperVerge Academy, the non-profit arm of HyperVerge, where we support learners from low-income backgrounds get jobs in tech by bringing together industry mentors and motivated learners. Because of this, SensAI is being tailor-made for learning and teaching programming but it can be used for any subject. If you are using SensAI and have any feedback for us, please consider joining the community (details below) or contacting us at `aman dot d at hyperverge dot org`.

If you want to contribute to SensAI, please look at the `Contributing` section below.

Watch the demo videos below to understand the features we currently offer for teachers and students:
<div style="display: flex; justify-content: space-between;">
  <div style="flex: 1;">
    <a href="https://www.loom.com/share/e23690f3b0a146d38a618fde09d6afdd">
      <p>SensAI demo (learner) - 18/10/24 - Watch Video</p>
    </a>
    <a href="https://www.loom.com/share/e23690f3b0a146d38a618fde09d6afdd">
      <img style="max-width:500px;" src="https://cdn.loom.com/sessions/thumbnails/e23690f3b0a146d38a618fde09d6afdd-0ef8650439c37e3c-full-play.gif">
    </a>
  </div>
  <div style="flex: 1;">
    <a href="https://www.loom.com/share/f1c19c3c34fc41fab727bdc9a5bfccf4">
      <p>SensAI demo (admin) - 18/10/24 - Watch Video</p>
    </a>
    <a href="https://www.loom.com/share/f1c19c3c34fc41fab727bdc9a5bfccf4">
      <img style="max-width:500px;" src="https://cdn.loom.com/sessions/thumbnails/f1c19c3c34fc41fab727bdc9a5bfccf4-9f67bb11ad04c53d-full-play.gif">
    </a>
  </div>
</div>

## Contributing
To learn more about making a contribution to SensAI, please see our [Contributing guide](./CONTRIBUTING.md).

## Local Setup

- Install `virtualenv`
- Create a new virtual environment (choose Python3.8+)
  ```
  virtualenv -p python3.10 venv
  ```
- Activate the virtual environment
  ```
  source venv/bin/activate
  ```
- Install packages
  ```
  pip install -r requirements.txt
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

The app is built using `streamlit` (entry point is `src/home.py`). We use `streamlit-cookies-manager` for storing a user's credentials and keeping them logged in (`src/auth.py`).
The API is built using `fastapi` (`src/api.py`). SQLite is used as the database. When developing locally, the sqlite db file is created in `src/db/`.

`src/lib` contains various helper functions.

Each of the individual app pages are under `src/pages`.

- `src/pages/admin.py`: Admin panel to add tasks/questions and verify the AI generated answers.
- `src/pages/task_list.py`: List of all verified tasks/questions that a learner can access.
- `src/pages/task.py`: Page for every task/question where the learner interacted with the AI tutor.

## Roadmap

Our public roadmap is live [here](https://hyperverge.notion.site/fa1dd0cef7194fa9bf95c28820dca57f?v=ec52c6a716e94df180dcc8ced3d87610). Go check it out!

## Community
We are building a community of creators, builders, teachers, learners, parents, entrepreneurs, non-profits and volunteers who are excited about the future of AI and education. If you identify as one and want to be part of it, [join](https://chat.whatsapp.com/LmiulDbWpcXIgqNK6fZyxe) our WhatsApp group.

Our thinking on how AI can impact Education is summarized in the mindmap below:
![ai + education thesis](./images/thesis.png)
