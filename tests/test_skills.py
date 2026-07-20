"""Tests for app.skills — PhraseMatcher skill extraction + spaCy NER."""

from app.skills import extract_skills, extract_skills_and_entities


def test_extract_skills_finds_known_terms(resume_text):
    skills = extract_skills(resume_text)
    for expected in ("python", "fastapi", "docker", "sql"):
        assert expected in skills


def test_multiword_skill_matched(resume_text):
    # "machine learning" exercises the multi-word, case-insensitive matcher.
    assert "machine learning" in extract_skills(resume_text)


def test_skills_are_sorted_and_unique(resume_text):
    skills = extract_skills(resume_text)
    assert skills == sorted(skills)
    assert len(skills) == len(set(skills))


def test_extract_skills_and_entities_shape(resume_text):
    result = extract_skills_and_entities(resume_text)
    assert set(result.keys()) == {"skills", "entities"}
    assert set(result["entities"].keys()) == {"PERSON", "ORG", "DATE"}


def test_person_entity_present(resume_text):
    entities = extract_skills_and_entities(resume_text)["entities"]
    # The candidate's name should be detected among PERSON entities.
    assert any("Jane" in p for p in entities["PERSON"])


def test_empty_text_returns_empty_skills():
    assert extract_skills("") == []
