# SensAI AI


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

## Running locally

```
cd app; uvicorn main:app --reload --port 8001
```

The app will be hosted on http://localhost:3000.
The docs will be available on http://localhost:3000/docs