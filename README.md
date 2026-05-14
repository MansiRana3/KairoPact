# KairoPact Assignment

This is a minimal document analysis workflow built with FastAPI, LangGraph, Pinecone, Langfuse, Gemini API, and Streamlit.

The project takes a short TXT or PDF document, retrieves relevant content from it, and returns a structured answer with a summary and key flags.

## What it does

1. Accepts an uploaded TXT or PDF document and a user query.
2. Extracts text from the document.
3. Splits the text into overlapping chunks.
4. Creates embeddings for the chunks using Gemini.
5. Stores the chunk embeddings in Pinecone.
6. Retrieves the top 3 relevant chunks for the query.
7. Sends those chunks to a Gemini LLM.
8. Returns structured JSON with:
   - `summary`
   - `flags`
9. Logs the workflow in Langfuse with these spans:
   - `ingest_node`
   - `retrieve_node`
   - `synthesise_node`

## Architecture flow

The project follows a simple flow:

```text
Streamlit UI
  -> FastAPI router
  -> service.py
  -> LangGraph workflow
  -> ingest_node -> retrieve_node -> synthesise_node
  -> Pinecone / Gemini
  -> JSON response
```

File responsibilities:

- `streamlit_app.py` is only the demo UI.
- `app/v1/router.py` handles HTTP request and response only.
- `app/v1/service.py` owns the main business flow.
- `app/v1/graph.py` defines the three LangGraph nodes and their order.
- `app/v1/agents.py` contains Gemini API calls for embeddings and synthesis.
- `app/v1/utils.py` contains helper functions like text extraction and chunking.
- `app/v1/schemas.py` contains Pydantic models for request, response, and workflow state.
- `app/core/config.py` loads environment variables from `.env`.
- `app/core/prompts_and_instructions/synthesise_prompt.txt` contains the LLM prompt.

## Setup

Install dependencies:

```bash
uv sync
```

If `uv` is not directly available on Windows, use:

```bash
py -3.12 -m uv sync
```

Copy `.env.example` to `.env` and fill in the required keys.

```bash
copy .env.example .env
```

## Required environment variables

```env
GEMINI_API_KEY=
GEMINI_EMBEDDING_MODEL=
GEMINI_LLM_MODEL=

PINECONE_API_KEY=
PINECONE_INDEX_NAME=
PINECONE_DIMENSION=
PINECONE_CLOUD=
PINECONE_REGION=

LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=

STREAMLIT_BACKEND_URL=
LOG_LEVEL=
```

## Pinecone index

The Pinecone index must match the embedding dimension used by the app.

For this project, the app is configured to use:

```env
PINECONE_DIMENSION=384
```

Create a Pinecone index with:

```text
dimension: 384
metric: cosine
```

If the index already exists with a different dimension, create a new index or recreate it with the correct dimension.

## Run FastAPI

```bash
uv run uvicorn main:app --reload
```

On Windows, if needed:

```bash
py -3.12 -m uv run uvicorn main:app --reload
```

The API endpoint is:

```text
POST /v1/analyse-document
```

It expects:

- multipart file field: `file`
- form field: `query`

Supported file types:

- `.txt`
- `.pdf`

## Run Streamlit

In a second terminal:

```bash
uv run streamlit run streamlit_app.py
```

On Windows, if needed:

```bash
py -3.12 -m uv run streamlit run streamlit_app.py
```

The Streamlit app lets the user upload a TXT or PDF file, enter a query, and view the result as:

- Summary
- Flags
- Debug JSON

## Check Langfuse traces

1. Start the FastAPI app with valid Langfuse environment variables.
2. Run a document analysis request from Streamlit or the API.
3. Open the Langfuse project.
4. Open the latest `analyse_document` trace.
5. Confirm that it contains:
   - `ingest_node`
   - `retrieve_node`
   - `synthesise_node`

## Example output

```json
{
  "summary": "The document highlights governance, staffing, and funding risks within the organisation. It points to concerns around leadership succession, institutional knowledge concentration, and donor dependency.",
  "flags": [
    "Leadership succession risk",
    "Institutional knowledge concentration",
    "Donor dependency",
    "Staff clarity and culture concerns"
  ]
}
```

## Verification

Run these checks before committing:

```bash
uv run pytest -x
uv run ruff check app/
uv run mypy app/
```

On Windows, if needed:

```bash
py -3.12 -m uv run pytest -x
py -3.12 -m uv run ruff check app/
py -3.12 -m uv run mypy app/
```

## Notes

Real API keys should only be kept in `.env`.

Do not commit:

- `.env`
- `.venv/`
- cache folders
- log files
