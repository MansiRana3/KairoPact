from __future__ import annotations

from types import SimpleNamespace
from typing import Sequence

import pytest

from app.core.config import Settings
from app.v1.schemas import AnalysisResponse, EmbeddingBatch, RetrievedChunk
from app.v1.service import DocumentAnalysisService
from app.v1.utils import build_doc_id


class FakeIndex:
    def __init__(self) -> None:
        self.upsert_calls: list[dict[str, object]] = []
        self.query_calls: list[dict[str, object]] = []

    def upsert(self, *, vectors: list[dict[str, object]], namespace: str) -> None:
        self.upsert_calls.append({"vectors": vectors, "namespace": namespace})

    def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        include_metadata: bool,
    ) -> SimpleNamespace:
        self.query_calls.append(
            {
                "namespace": namespace,
                "vector": vector,
                "top_k": top_k,
                "include_metadata": include_metadata,
            }
        )
        return SimpleNamespace(
            matches=[
                {
                    "score": 0.95,
                    "metadata": {
                        "text": "Late notice was sent to customers.",
                        "doc_id": namespace,
                        "chunk_index": 0,
                        "source": "sample.txt",
                    },
                },
                {
                    "score": 0.87,
                    "metadata": {
                        "text": "The audit trail is incomplete.",
                        "doc_id": namespace,
                        "chunk_index": 1,
                        "source": "sample.txt",
                    },
                },
            ]
        )


class StubDocumentAnalysisService(DocumentAnalysisService):
    def __init__(self, fake_index: FakeIndex) -> None:
        settings = Settings(
            gemini_api_key="test-gemini-key",
            pinecone_dimension=3,
            pinecone_api_key="test-pinecone-key",
            langfuse_public_key="test-langfuse-public",
            langfuse_secret_key="test-langfuse-secret",
        )
        self.fake_index = fake_index
        super().__init__(settings=settings)

    def _get_or_create_index(self) -> FakeIndex:
        return self.fake_index

    async def _embed_texts(self, texts: Sequence[str], task_type: str) -> EmbeddingBatch:
        assert task_type in {"RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"}
        return EmbeddingBatch(embeddings=[[0.1, 0.2, 0.3] for _ in texts], model="test-model")

    async def _synthesise_chunks(
        self,
        query: str,
        chunks: Sequence[RetrievedChunk],
    ) -> AnalysisResponse:
        assert query == "What are the main issues?"
        assert len(chunks) == 2
        return AnalysisResponse(
            summary="Customers received late notices and the audit trail is incomplete.",
            flags=["Late customer notice", "Missing audit trail"],
        )


@pytest.mark.asyncio
async def test_analyse_document_runs_full_flow() -> None:
    fake_index = FakeIndex()
    service = StubDocumentAnalysisService(fake_index=fake_index)
    document_text = (
        "Customers were notified late about the policy update. "
        "The team also noted that the audit trail is incomplete."
    )

    result = await service.analyse_document(
        file_bytes=document_text.encode("utf-8"),
        filename="sample.txt",
        content_type="text/plain",
        query="What are the main issues?",
    )

    expected_doc_id = build_doc_id("sample.txt", document_text)

    assert result.summary.startswith("Customers received late notices")
    assert result.flags == ["Late customer notice", "Missing audit trail"]
    assert fake_index.upsert_calls[0]["namespace"] == expected_doc_id
    assert fake_index.query_calls[0]["namespace"] == expected_doc_id
    assert fake_index.query_calls[0]["top_k"] == 3

    upsert_vectors = fake_index.upsert_calls[0]["vectors"]
    assert isinstance(upsert_vectors, list)
    first_vector = upsert_vectors[0]
    assert isinstance(first_vector, dict)
    metadata = first_vector["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["source"] == "sample.txt"


@pytest.mark.asyncio
async def test_analyse_document_rejects_empty_query() -> None:
    fake_index = FakeIndex()
    service = StubDocumentAnalysisService(fake_index=fake_index)

    with pytest.raises(ValueError, match="The query cannot be empty."):
        await service.analyse_document(
            file_bytes=b"some text",
            filename="sample.txt",
            content_type="text/plain",
            query="   ",
        )
