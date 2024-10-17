# SensAI - A Socratic AI Tutor

**For Teachers** (`http://localhost:8501/admin`)
- Add a task, use AI to generate the answer and verify it. A task is the same as a question.
- Bulk upload tasks instead of feeding tasks one by one. 
  - Just add a CSV file with the following columns: `Name`, `Description`, `Tags`
  - Once the answers are generated, select `Verify Mode` to verify the answers and save your verification.
- Get the entire chat history. Make a GET request to `http://localhost:8001/chat_history`. You can connect this with Google Sheets using AppScript to view the entire chat history on Sheets.
- Select one or more tasks and delete them if you want to.

**For learners** (`http://localhost:8501/`)
- See the list of verified tasks that you can work on by visiting `http://localhost:8501/task_list`
- Click on one of the tasks and start attempting it. The AI tutor will help guide the learner with any doubts they might have and assess their responses. Students will receive personalized feedback on their answers and guidance tailored to their needs.

Many more things to come soon, for both learners and teachers.

Watch the demo below to understand more:
<div>
  <a href="https://www.loom.com/share/a763d6c5cd4c4bb38e74f1f72c4aa48c">
    <img style="max-width:300px;" src="https://cdn.loom.com/sessions/thumbnails/a763d6c5cd4c4bb38e74f1f72c4aa48c-ba42b26917ee9648-full-play.gif">
  </a>
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

## What's New
**2024-09-22**
- Fixed a bug where an error was thrown upon toggling the "Show Code Editor" button while creating a task.
- Updated the list of tags that can be used while creating a task.
- Removed LangChain for streaming JSON responses. Using Instructor and a much simpler approach overall to stream JSON responses.
- Improved the system prompt to not give away the answer, to maintain formatting and diversity in the feedback while also including an emojis in the feedback from time to time.
- Fixed the widget duplication error being thrown on the task page when rendering the chat UI.

**2024-09-21**
- Added support for a dev container to test new features before pushing to prod.
- Fixed the bug where adding code to the code editor kept refreshing the entire page making for a page experience. Instead of automatically updating the session state variables where the code for each language is stored as one is typing, the variables are now set only after the learner manually clicks the "Run Code" button.
- Updated the Task UI to give more space to the code editor and restrict the learner's chat input to the chat section of the page.
- Removed the `Show Code Preview` button from the task creator page and converted `coding_language` to a list of languages so that we avoid hardcoding which languages to show in the code editor and everything is clearly specified by the task creator.

**2024-09-16**
- Fixed the bug where only one email was being used globally across all users. Used a hack for storing the email in the session state and using the query params in the URL to set it.
- @shekhar32 [fixed](https://gitlab.com/hvacademy/sensai-ai/-/merge_requests/4) the bug where status was being set for all tasks without checking if tasks exist
- Added support for filtering tasks by tags for admin
- Added support for bulk updating task attributes by the admin
- Code editor for coding questions has been added along with an option to show code preview for the code (supports HTML, CSS, JS for now)
- Layout has been set to wide mode for each page
- Adjusted the sticky container's theme to match the theme of the app

**2024-09-15**
- Added support for fetching all tasks
- Added LICENSE
- Added Contributing guidelines

**2024-09-13**
- AI response returned as a JSON with the keys `feedback` and `is_solved`. The feedback is streamed to the user. `is_solved` indicates if the question has been solved.
- The task title/description is now inside a sticky container that remains fixed on the top of the task page. If the task has been solved, a green tick mark appears next to the task name.
- In the list of all tasks for a learner, the solved tasks are marked as a green row with a tick mark.