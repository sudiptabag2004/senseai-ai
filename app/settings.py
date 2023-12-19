import os
from pydantic import BaseSettings


def get_env_file_path():
    return ".env"


class Settings(BaseSettings):
    openai_api_key: str
    openai_org_id: str
    # wandb_api_key: Optional[str]

    class Config:
        env_file = get_env_file_path()


settings = Settings()
