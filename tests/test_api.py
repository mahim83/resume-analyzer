"""Integration tests for the FastAPI /analyze endpoint via TestClient."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_ok():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_docx_without_jd(docx_bytes):
    resp = client.post(
        "/analyze",
        files={"file": ("sample_resume.docx", docx_bytes)},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "python" in body["skills_found"]
    assert body["match_score"] is None
    assert body["missing_skills"] == []
    assert isinstance(body["suggestions"], list)
    assert set(body["entities"].keys()) == {"PERSON", "ORG", "DATE"}


def test_analyze_pdf_with_jd(pdf_bytes, job_description):
    resp = client.post(
        "/analyze",
        files={"file": ("sample_resume.pdf", pdf_bytes)},
        data={"jd_text": job_description},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["match_score"] is not None
    assert body["match_score"] > 60
    assert "graphql" in [m.lower() for m in body["missing_skills"]]


def test_unsupported_type_returns_415():
    resp = client.post("/analyze", files={"file": ("resume.txt", b"hello")})
    assert resp.status_code == 415


def test_corrupt_docx_returns_422():
    resp = client.post(
        "/analyze",
        files={"file": ("resume.docx", b"not a real docx")},
    )
    assert resp.status_code == 422


def test_missing_file_returns_422():
    # No file part at all -> FastAPI validation error.
    resp = client.post("/analyze")
    assert resp.status_code == 422
