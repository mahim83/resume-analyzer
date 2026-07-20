"""Shared pytest fixtures."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def docx_bytes() -> bytes:
    return (FIXTURES / "sample_resume.docx").read_bytes()


@pytest.fixture(scope="session")
def pdf_bytes() -> bytes:
    return (FIXTURES / "sample_resume.pdf").read_bytes()


@pytest.fixture(scope="session")
def resume_text(docx_bytes) -> str:
    """Extracted text of the sample resume (used by NLP tests)."""
    from app.parser import extract_text

    return extract_text(docx_bytes, "sample_resume.docx")


@pytest.fixture(scope="session")
def job_description() -> str:
    return (
        "We are hiring a backend engineer proficient in Python, FastAPI, Docker, "
        "Kubernetes, and AWS. Experience with GraphQL and Redis is a plus. You "
        "will design REST APIs and deploy microservices to the cloud."
    )
