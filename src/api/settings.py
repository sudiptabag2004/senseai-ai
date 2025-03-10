from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    google_client_id: str

    model_config = SettingsConfigDict(env_file="api/.env")


@lru_cache
def get_settings():
    return Settings()


settings = get_settings()
