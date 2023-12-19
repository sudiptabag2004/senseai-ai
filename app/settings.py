import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_org_id: str
    wandb_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
