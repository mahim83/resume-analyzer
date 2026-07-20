"""Pydantic response models for the API."""

from typing import Optional

from pydantic import BaseModel


class AnalysisResult(BaseModel):
    """Structured result returned by ``POST /analyze``."""

    skills_found: list[str]
    entities: dict
    match_score: Optional[float] = None
    missing_skills: list[str] = []
    suggestions: list[str]
