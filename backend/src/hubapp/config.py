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

    # Which LLM provider the identify/discover agent loops use — passed straight
    # to ragapp.llm.factory.create_llm_client(), so it accepts the same values
    # ("ollama"/"openai"/"anthropic"). None (the default) means "same as
    # ragapp's own LLM_PROVIDER". Tool-calling reliability varies a lot by
    # model — llama3.2:3b does support it, but a hosted model (set this to
    # "anthropic" or "openai" with the matching API key configured) will
    # generally be more consistent at picking the right tool and knowing when
    # to stop. Separate from LLM_PROVIDER because the agent loops are a very
    # different workload (occasional, tool-calling, latency-tolerant) from RAG
    # chat (frequent, streaming, local-first by default).
    agent_llm_provider: str | None = None


settings = Settings()
