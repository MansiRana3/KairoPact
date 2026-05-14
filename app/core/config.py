from __future__ import annotations

from functools import lru_cache
from typing import cast

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field(validation_alias="GEMINI_API_KEY")
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001",
        validation_alias="GEMINI_EMBEDDING_MODEL",
    )
    gemini_llm_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias="GEMINI_LLM_MODEL",
    )
    pinecone_api_key: str = Field(validation_alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field(
        default="kairopact-assignment",
        validation_alias="PINECONE_INDEX_NAME",
    )
    pinecone_dimension: int = Field(validation_alias="PINECONE_DIMENSION")
    pinecone_cloud: str = Field(default="aws", validation_alias="PINECONE_CLOUD")
    pinecone_region: str = Field(default="us-east-1", validation_alias="PINECONE_REGION")
    langfuse_public_key: str = Field(validation_alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(validation_alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        validation_alias=AliasChoices("LANGFUSE_HOST", "LANGFUSE_BASE_URL"),
    )
    streamlit_backend_url: str = Field(
        default="http://127.0.0.1:8000",
        validation_alias=AliasChoices("STREAMLIT_BACKEND_URL", "BACKEND_URL"),
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # BaseSettings reads required values from the environment at runtime.
    return cast(Settings, Settings())  # type: ignore[call-arg]
