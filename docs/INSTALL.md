## Installation

### Using Docker

```
docker compose -f docker-compose.ai.dev.yml pull
docker compose -f docker-compose.ai.dev.yml -p sensai-dev up -d
```

Once the containers are up, the app will be hosted on http://localhost:8501 and the api will be hosted on http://localhost:8001.

### From source
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
  pip install -r requirements-dev.txt
  ```
- Install `ffmpeg` and `poppler`

  For Ubuntu:
  ```
  sudo apt-get update && sudo apt-get install ffmpeg poppler-utils
  ```
  For MacOS:
  ```
  brew install ffmpeg poppler
  export PATH="/path/to/poppler/bin:$PATH"
  ```
  You can get the path to poppler using `brew list poppler`
- Copy `src/lib/.env.example` to `src/lib/.env` and set the OpenAI credentials. Refer to [ENV.md](./ENV.md) for more details on the environment variables.
- Copy `src/.streamlit/secrets.example.toml` to `src/.streamlit/secrets.toml` and set the Google credentials. Refer [this](https://github.com/kajarenc/stauthlib/tree/main) for more details on how to set up the credentials.
- Running the app locally
    ```
    cd src; streamlit run home.py
    ```

    The app will be hosted on http://localhost:8501.
- Running the API locally
    ```
    cd src; uvicorn api:app --reload --port 8001
    ```

    The api will be hosted on http://localhost:8001.
    The docs will be available on http://localhost:8001/docs


### Additional steps for contributors
- Set up `pre-commit` hooks. `pre-commit` should already be installed while installing requirements from the `requirements-dev.txt` file.
  ```
  pre-commit install
  ```
