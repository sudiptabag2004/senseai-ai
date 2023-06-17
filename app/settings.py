import os
from pydantic import BaseSettings


def get_env_file_path() -> str:
    if os.getenv("ENV") == "production":
        return ".env.production"
    elif os.getenv("ENV") == "staging":
        return ".env.staging"
    return ".env"


class Settings(BaseSettings):
    openai_api_key: str
    openai_org_id: str
    wandb_api_key: str

    class Config:
        env_file = get_env_file_path()


settings = Settings()
