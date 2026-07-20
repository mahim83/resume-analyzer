"""FastAPI application exposing the resume-analysis pipeline."""

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .matcher import match_score, missing_skills
from .models import AnalysisResult
from .parser import extract_text
from .skills import extract_skills_and_entities
from .suggestions import generate_suggestions

app = FastAPI(
    title="Resume Analyzer API",
    description=(
        "Analyzes resumes with spaCy (PhraseMatcher skill extraction + NER) "
        "and sentence-transformers (semantic job-description matching)."
    ),
    version="1.0.0",
)

# Permissive CORS so the Streamlit frontend (a different origin/port) can call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_EXTENSIONS = (".pdf", ".docx")


@app.get("/")
def root() -> dict:
    """Simple liveness/info endpoint."""
    return {"status": "ok", "service": "resume-analyzer", "docs": "/docs"}


@app.post("/analyze", response_model=AnalysisResult)
async def analyze(
    file: UploadFile = File(...),
    jd_text: str = Form(None),
) -> AnalysisResult:
    """Analyze an uploaded resume, optionally matching it against a JD.

    Pipeline: read bytes -> extract text -> extract skills & entities ->
    (optional) JD match score + missing skills -> rule-based suggestions.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(_ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a .pdf or .docx file.",
        )

    file_bytes = await file.read()

    try:
        text = extract_text(file_bytes, filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    extracted = extract_skills_and_entities(text)
    skills_found = extracted["skills"]

    score = None
    missing: list[str] = []
    if jd_text and jd_text.strip():
        score = match_score(text, jd_text)
        missing = missing_skills(skills_found, jd_text)

    suggestions = generate_suggestions(text)

    return AnalysisResult(
        skills_found=skills_found,
        entities=extracted["entities"],
        match_score=score,
        missing_skills=missing,
        suggestions=suggestions,
    )
