"""Tests for app.matcher — semantic JD match score and missing skills."""

from app.matcher import match_score, missing_skills

UNRELATED = (
    "We are looking for a pastry chef to design dessert menus, bake breads, "
    "and manage a busy restaurant kitchen during weekend service."
)


def test_related_scores_higher_than_unrelated(resume_text, job_description):
    related = match_score(resume_text, job_description)
    unrelated = match_score(resume_text, UNRELATED)
    assert related > 60
    assert related > unrelated


def test_score_is_bounded(resume_text, job_description):
    score = match_score(resume_text, job_description)
    assert 0.0 <= score <= 100.0


def test_empty_text_scores_zero(job_description):
    assert match_score("", job_description) == 0.0


def test_missing_skills_flags_absent_jd_skills(job_description):
    have = ["python", "fastapi", "docker", "kubernetes", "aws"]
    missing = [m.lower() for m in missing_skills(have, job_description)]
    assert "graphql" in missing
    assert "redis" in missing
    # Skills already present must not be reported as missing.
    assert "python" not in missing


def test_missing_skills_empty_when_all_present(job_description):
    from app.skills import extract_skills

    have = extract_skills(job_description)
    assert missing_skills(have, job_description) == []
