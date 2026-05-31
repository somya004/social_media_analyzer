from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Required — app will not start without these
    gemini_api_key: str
    apify_api_token: str

    # Optional with sensible defaults
    chroma_persist_dir: str = "./chroma_db"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    gemini_model: str = "gemini-1.5-flash"

    cors_origins: List[str] = ["http://localhost:3000"]
    log_level: str = "INFO"
    debug: bool = False

    @field_validator("log_level")
    @classmethod
    def normalise_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
