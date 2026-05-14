from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any, Sequence, cast

from google import genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.core.logger import get_logger
from app.v1.schemas import AnalysisResponse, EmbeddingBatch, RetrievedChunk
from app.v1.utils import normalise_flags

logger = get_logger(__name__)
PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "core"
    / "prompts_and_instructions"
    / "synthesise_prompt.txt"
)


def _get_gemini_client(settings: Settings) -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


@lru_cache(maxsize=1)
def _load_synthesise_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _format_retrieved_chunks(chunks: Sequence[RetrievedChunk]) -> str:
    if not chunks:
        return "No chunks were retrieved."

    lines: list[str] = []
    for chunk in chunks:
        lines.append(
            f"Chunk {chunk.chunk_index} | source={chunk.source} | score={chunk.score}\n{chunk.text}"
        )
    return "\n\n".join(lines)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
async def embed_texts(
    texts: Sequence[str],
    task_type: str,
    settings: Settings | None = None,
) -> EmbeddingBatch:
    active_settings = settings or get_settings()
    client = _get_gemini_client(active_settings)

    if not texts:
        return EmbeddingBatch(embeddings=[], model=active_settings.gemini_embedding_model)

    start_time = perf_counter()
    response = await client.aio.models.embed_content(
        model=active_settings.gemini_embedding_model,
        contents=cast(Any, list(texts)),
        config={
            "output_dimensionality": active_settings.pinecone_dimension,
            "task_type": task_type,
        },
    )
    elapsed = perf_counter() - start_time

    usage = getattr(response, "metadata", None)
    logger.info(
        "embed_texts | %.2fs | model=%s billable_characters=%s batch_size=%s",
        elapsed,
        active_settings.gemini_embedding_model,
        getattr(usage, "billable_character_count", None),
        len(texts),
    )

    embeddings = response.embeddings or []
    return EmbeddingBatch(
        embeddings=[embedding.values or [] for embedding in embeddings],
        model=active_settings.gemini_embedding_model,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
async def synthesise_chunks(
    query: str,
    chunks: Sequence[RetrievedChunk],
    settings: Settings | None = None,
) -> AnalysisResponse:
    active_settings = settings or get_settings()
    client = _get_gemini_client(active_settings)
    prompt = _load_synthesise_prompt()

    user_message = (
        f"User query:\n{query}\n\n"
        f"Retrieved chunks:\n{_format_retrieved_chunks(chunks)}"
    )

    start_time = perf_counter()
    response = await client.aio.models.generate_content(
        model=active_settings.gemini_llm_model,
        contents=user_message,
        config={
            "system_instruction": prompt,
            "response_mime_type": "application/json",
            "response_schema": AnalysisResponse,
            "temperature": 0,
        },
    )
    elapsed = perf_counter() - start_time

    usage = response.usage_metadata
    logger.info(
        "synthesise_chunks | %.2fs | prompt_tokens=%s completion_tokens=%s total_tokens=%s",
        elapsed,
        getattr(usage, "prompt_token_count", None),
        getattr(usage, "candidates_token_count", None),
        getattr(usage, "total_token_count", None),
    )

    parsed = cast(AnalysisResponse | None, response.parsed)
    if parsed is None:
        raise ValueError("Gemini did not return a structured response.")

    return AnalysisResponse(
        summary=parsed.summary.strip(),
        flags=normalise_flags(parsed.flags),
    )
