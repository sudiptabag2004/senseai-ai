import os
from os.path import join
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from functools import lru_cache

if "AWS_ACCESS_KEY_ID" not in os.environ:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    load_dotenv(join(root_dir, ".env.aws"))


class Settings(BaseSettings):
    google_client_id: str
    openai_api_key: str
    s3_bucket_name: str
    s3_folder_name: str

    model_config = SettingsConfigDict(env_file="api/.env")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
