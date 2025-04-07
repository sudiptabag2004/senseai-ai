import os
from os.path import join
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
from functools import lru_cache

root_dir = os.path.dirname(os.path.abspath(__file__))
env_path = join(root_dir, ".env.aws")
if os.path.exists(env_path):
    load_dotenv(env_path)


class Settings(BaseSettings):
    google_client_id: str
    openai_api_key: str
    s3_bucket_name: str
    s3_folder_name: str

    model_config = SettingsConfigDict(env_file=join(root_dir, ".env"))


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
