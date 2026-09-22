from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    # Same env var name/value as ragapp.config.Settings.database_url — both read the
    # same .env file (this app's own), so they end up pointed at the same database
    # without any explicit wiring. See docs/specs/01-architecture.md.
    database_url: str = "postgresql://hubapp:hubapp@127.0.0.1:5433/hubapp"

    tavily_api_key: str | None = None

    # Where retained copies of ingested manuals live (so they can be viewed/
    # downloaded later, not just chunked into the vector store and discarded).
    manuals_dir: str = "data/manuals"


settings = Settings()
