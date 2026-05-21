from __future__ import annotations

from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


    ssw_base_url: str = Field(
        default="https://api.moonshot.cn/v1",
        alias="SSW_BASE_URL"
    )
    ssw_model: str = Field(default="kimi-k2.6", alias="SSW_MODEL")
    ssw_api_key: str | None = Field(default=None, alias="SSW_API_KEY")

    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
  

def get_settings() -> Settings:
    settings = Settings()
    return settings
