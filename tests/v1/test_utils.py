from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.v1 import utils
from app.v1.utils import (
    build_doc_id,
    chunk_text,
    decode_text_file,
    extract_document_text,
    normalise_flags,
)


def test_chunk_text_creates_overlapping_chunks() -> None:
    text = "A" * 700

    chunks = chunk_text(text, chunk_size=500, chunk_overlap=100)

    assert len(chunks) == 2
    assert len(chunks[0]) == 500
    assert len(chunks[1]) == 300
    assert chunks[0][-100:] == chunks[1][:100]


def test_chunk_text_rejects_invalid_overlap() -> None:
    try:
        chunk_text("hello", chunk_size=100, chunk_overlap=100)
    except ValueError as exc:
        assert str(exc) == "chunk_overlap must be smaller than chunk_size."
    else:
        raise AssertionError("chunk_text should reject chunk_overlap >= chunk_size.")


def test_build_doc_id_is_stable() -> None:
    doc_id_one = build_doc_id("Sample Document.txt", "hello world")
    doc_id_two = build_doc_id("Sample Document.txt", "hello world")

    assert doc_id_one == doc_id_two
    assert doc_id_one.startswith("sample-document-txt-")


def test_decode_text_file_falls_back_to_replace() -> None:
    decoded = decode_text_file(b"hello\xffworld")

    assert "hello" in decoded
    assert "world" in decoded


def test_extract_document_text_reads_txt_file() -> None:
    text = extract_document_text(b"hello world", "notes.txt", "text/plain")

    assert text == "hello world"


def test_extract_document_text_rejects_unsupported_file_type() -> None:
    with pytest.raises(ValueError, match=r"Unsupported file type"):
        extract_document_text(b"{}", "notes.json", "application/json")


def test_extract_document_text_reads_pdf_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakePdfReader:
        def __init__(self, _: object) -> None:
            self.pages = [
                FakePage("First page text"),
                FakePage("Second page text"),
            ]

    monkeypatch.setattr(utils, "PdfReader", FakePdfReader)

    text = extract_document_text(b"%PDF-1.4", "report.pdf", "application/pdf")

    assert text == "First page text\nSecond page text"


def test_normalise_flags_strips_empty_values() -> None:
    assert normalise_flags(["  Risk  ", "", "  "]) == ["Risk"]
