"""Tests for app.parser — PDF/DOCX text extraction and error handling."""

import pytest

from app.parser import extract_text


def test_extract_docx(docx_bytes):
    text = extract_text(docx_bytes, "sample_resume.docx")
    assert "Jane Doe" in text
    assert "FastAPI" in text


def test_extract_pdf(pdf_bytes):
    text = extract_text(pdf_bytes, "sample_resume.pdf")
    assert "Jane Doe" in text
    assert "FastAPI" in text


def test_case_insensitive_extension(docx_bytes):
    # Uppercase extension should still be recognized.
    text = extract_text(docx_bytes, "RESUME.DOCX")
    assert text.strip()


def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"whatever", "resume.txt")


def test_corrupt_docx_raises_valueerror():
    # A non-zip payload with a .docx name must surface as ValueError (-> API 422),
    # not an uncaught library exception.
    with pytest.raises(ValueError):
        extract_text(b"this is not a real docx", "resume.docx")


def test_empty_pdf_bytes_raises():
    with pytest.raises(ValueError):
        extract_text(b"", "resume.pdf")
