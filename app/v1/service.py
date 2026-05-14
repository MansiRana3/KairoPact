from __future__ import annotations

import asyncio
import time
from functools import lru_cache
from typing import Any, Sequence

from langfuse import Langfuse, observe
from pinecone import Pinecone, ServerlessSpec

from app.core.config import Settings, get_settings
from app.core.logger import configure_logging, get_logger
from app.v1.agents import embed_texts, synthesise_chunks
from app.v1.graph import build_document_analysis_graph
from app.v1.schemas import AnalysisResponse, DocumentAnalysisState, EmbeddingBatch, RetrievedChunk
from app.v1.utils import build_doc_id, chunk_text, extract_document_text


class DocumentAnalysisService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        configure_logging(self.settings.log_level)
        self.logger = get_logger(__name__)
        self._langfuse_client = Langfuse(
            public_key=self.settings.langfuse_public_key,
            secret_key=self.settings.langfuse_secret_key,
            host=self.settings.langfuse_host,
        )
        self._pinecone_client: Pinecone | None = None
        self._pinecone_index: Any | None = None
        self._graph = build_document_analysis_graph(
            ingest_node=self.ingest_node,
            retrieve_node=self.retrieve_node,
            synthesise_node=self.synthesise_node,
        )

    def _update_current_span(
        self,
        *,
        input_data: Any | None = None,
        output_data: Any | None = None,
    ) -> None:
        self._langfuse_client.update_current_span(input=input_data, output=output_data)

    def _get_pinecone_client(self) -> Pinecone:
        if self._pinecone_client is None:
            self._pinecone_client = Pinecone(api_key=self.settings.pinecone_api_key)
        return self._pinecone_client

    def _wait_for_index_ready(self, client: Pinecone) -> None:
        timeout_at = time.time() + 60
        while time.time() < timeout_at:
            description = client.describe_index(self.settings.pinecone_index_name)
            status = getattr(description, "status", {})
            is_ready = bool(status.get("ready")) if isinstance(status, dict) else bool(
                getattr(status, "ready", False)
            )
            if is_ready:
                return
            time.sleep(1)
        raise TimeoutError("Timed out while waiting for the Pinecone index to become ready.")

    def _get_or_create_index(self) -> Any:
        if self._pinecone_index is not None:
            return self._pinecone_index

        client = self._get_pinecone_client()
        indexes = client.list_indexes()
        index_names = set(indexes.names())

        if self.settings.pinecone_index_name not in index_names:
            client.create_index(
                name=self.settings.pinecone_index_name,
                dimension=self.settings.pinecone_dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud=self.settings.pinecone_cloud,
                    region=self.settings.pinecone_region,
                ),
            )
            self._wait_for_index_ready(client)
        else:
            description = client.describe_index(self.settings.pinecone_index_name)
            current_dimension = getattr(description, "dimension", None)
            if current_dimension != self.settings.pinecone_dimension:
                raise ValueError(
                    "Pinecone index dimension mismatch. "
                    "Update PINECONE_DIMENSION so it matches the Gemini embedding output dimension."
                )

        self._pinecone_index = client.Index(self.settings.pinecone_index_name)
        return self._pinecone_index

    async def _embed_texts(self, texts: Sequence[str], task_type: str) -> EmbeddingBatch:
        return await embed_texts(texts=texts, task_type=task_type, settings=self.settings)

    async def _synthesise_chunks(
        self,
        query: str,
        chunks: Sequence[RetrievedChunk],
    ) -> AnalysisResponse:
        return await synthesise_chunks(query=query, chunks=chunks, settings=self.settings)

    def _match_to_chunk(self, match: Any) -> RetrievedChunk:
        metadata = getattr(match, "metadata", None)
        score = getattr(match, "score", None)

        if isinstance(match, dict):
            metadata = match.get("metadata", metadata)
            score = match.get("score", score)

        metadata_dict = metadata or {}
        return RetrievedChunk(
            text=str(metadata_dict.get("text", "")),
            doc_id=str(metadata_dict.get("doc_id", "")),
            chunk_index=int(metadata_dict.get("chunk_index", 0)),
            source=str(metadata_dict.get("source", "uploaded_document")),
            score=float(score) if score is not None else None,
        )

    @observe(name="analyse_document")
    async def analyse_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        content_type: str | None,
        query: str,
    ) -> AnalysisResponse:
        document_text = extract_document_text(file_bytes, filename, content_type)
        cleaned_query = query.strip()
        source = filename or "uploaded_document.txt"

        if not document_text.strip():
            raise ValueError("The uploaded file is empty.")
        if not cleaned_query:
            raise ValueError("The query cannot be empty.")

        state: DocumentAnalysisState = {
            "document_text": document_text,
            "source": source,
            "query": cleaned_query,
            "doc_id": build_doc_id(source, document_text),
        }

        result = await self._graph.ainvoke(state)
        analysis = result["analysis"]
        self.logger.info("analyse_document_result | %s", analysis.model_dump_json())
        return analysis

    @observe(name="ingest_node")
    async def ingest_node(self, state: DocumentAnalysisState) -> dict[str, Any]:
        chunks = chunk_text(state["document_text"], chunk_size=500, chunk_overlap=100)
        if not chunks:
            raise ValueError("The uploaded file did not produce any text chunks.")

        self._update_current_span(
            input_data={
                "doc_id": state["doc_id"],
                "source": state["source"],
                "chunk_count": len(chunks),
            }
        )

        embedding_batch = await self._embed_texts(chunks, task_type="RETRIEVAL_DOCUMENT")
        if len(embedding_batch.embeddings) != len(chunks):
            raise ValueError("Embedding count did not match chunk count.")

        vectors = []
        for chunk_index, (chunk, embedding) in enumerate(
            zip(chunks, embedding_batch.embeddings, strict=True)
        ):
            vectors.append(
                {
                    "id": f"{state['doc_id']}-{chunk_index}",
                    "values": embedding,
                    "metadata": {
                        "text": chunk,
                        "doc_id": state["doc_id"],
                        "chunk_index": chunk_index,
                        "source": state["source"],
                    },
                }
            )

        index = await asyncio.to_thread(self._get_or_create_index)
        await asyncio.to_thread(index.upsert, vectors=vectors, namespace=state["doc_id"])

        self._update_current_span(output_data={"upserted_chunks": len(vectors)})
        return {"chunks": chunks}

    @observe(name="retrieve_node")
    async def retrieve_node(self, state: DocumentAnalysisState) -> dict[str, Any]:
        self._update_current_span(input_data={"doc_id": state["doc_id"], "query": state["query"]})

        query_embedding_batch = await self._embed_texts(
            [state["query"]],
            task_type="RETRIEVAL_QUERY",
        )
        query_vector = query_embedding_batch.embeddings[0]

        index = await asyncio.to_thread(self._get_or_create_index)
        query_result = await asyncio.to_thread(
            index.query,
            namespace=state["doc_id"],
            vector=query_vector,
            top_k=3,
            include_metadata=True,
        )

        matches = getattr(query_result, "matches", [])
        retrieved_chunks = [self._match_to_chunk(match) for match in matches]

        self._update_current_span(output_data={"retrieved_chunk_count": len(retrieved_chunks)})
        return {"retrieved_chunks": retrieved_chunks}

    @observe(name="synthesise_node")
    async def synthesise_node(self, state: DocumentAnalysisState) -> dict[str, Any]:
        retrieved_chunks = state.get("retrieved_chunks", [])
        self._update_current_span(
            input_data={
                "query": state["query"],
                "retrieved_chunk_count": len(retrieved_chunks),
            }
        )

        analysis = await self._synthesise_chunks(state["query"], retrieved_chunks)
        self._update_current_span(output_data=analysis.model_dump())
        return {"analysis": analysis}


@lru_cache(maxsize=1)
def get_document_analysis_service() -> DocumentAnalysisService:
    return DocumentAnalysisService()
