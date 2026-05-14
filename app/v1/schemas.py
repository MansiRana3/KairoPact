from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    summary: str = Field(description="A grounded 2-3 sentence summary.")
    flags: list[str] = Field(default_factory=list, description="Key issues or themes.")


class RetrievedChunk(BaseModel):
    text: str
    doc_id: str
    chunk_index: int
    source: str
    score: float | None = None


class EmbeddingBatch(BaseModel):
    embeddings: list[list[float]]
    model: str


class DocumentAnalysisState(TypedDict, total=False):
    document_text: str
    source: str
    query: str
    doc_id: str
    chunks: list[str]
    retrieved_chunks: list[RetrievedChunk]
    analysis: AnalysisResponse
