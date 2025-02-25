from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key_encryption_key: str

    model_config = SettingsConfigDict(env_file="api/.env")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
