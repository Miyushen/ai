from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "InsightAgent"
    app_version: str = "0.1.0"
    database_url: str = "postgresql+psycopg://insight:insight@localhost:5432/insight"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    openai_use_responses_api: bool = True
    openai_reasoning_effort: str = ""
    openai_verbosity: str = ""
    openai_max_completion_tokens: int = 0
    max_sql_rows: int = 200
    sql_timeout_ms: int = 10_000
    max_agent_retries: int = 2
    model_node_max_attempts: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()

