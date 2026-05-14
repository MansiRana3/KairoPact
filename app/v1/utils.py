from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


def decode_text_file(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("utf-8", errors="replace")


def extract_document_text(
    file_bytes: bytes,
    filename: str,
    content_type: str | None = None,
) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".txt" or content_type == "text/plain":
        return decode_text_file(file_bytes)

    if suffix == ".pdf" or content_type == "application/pdf":
        reader = PdfReader(BytesIO(file_bytes))
        page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n".join(page_text for page_text in page_texts if page_text)

    raise ValueError("Unsupported file type. Please upload a .txt or .pdf file.")


def chunk_text(text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0.")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size.")

    cleaned_text = text.strip()
    if not cleaned_text:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(cleaned_text):
        end = min(start + chunk_size, len(cleaned_text))
        chunk = cleaned_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(cleaned_text):
            break
        start = end - chunk_overlap

    return chunks


def build_doc_id(source: str, text: str) -> str:
    safe_source = re.sub(r"[^a-z0-9]+", "-", source.lower()).strip("-") or "uploaded-document"
    digest = hashlib.sha1(f"{source}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"{safe_source}-{digest}"


def normalise_flags(flags: list[str]) -> list[str]:
    cleaned_flags = [flag.strip() for flag in flags if flag.strip()]
    return cleaned_flags
