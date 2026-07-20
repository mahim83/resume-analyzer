"""Job-description matching via sentence-transformer embeddings.

The embedding model is loaded once at import time. On very memory-constrained
hosts (e.g. a 512MB free tier) this import is the largest allocation; if that
becomes a problem, switch to lazy loading on first ``match_score`` call.
"""

from sentence_transformers import SentenceTransformer, util

from .skills import extract_skills

# all-MiniLM-L6-v2 is a small (~80MB) general-purpose embedding model that
# captures semantic similarity well while staying deployable on small hosts.
model = SentenceTransformer("all-MiniLM-L6-v2")


def match_score(resume_text: str, jd_text: str) -> float:
    """Semantic similarity between a resume and a job description, 0-100.

    Encodes both texts, takes the cosine similarity of the embeddings, clamps
    to ``[0, 1]`` (embeddings can produce small negatives for unrelated text),
    and scales to a 0-100 score rounded to one decimal place.
    """
    if not resume_text.strip() or not jd_text.strip():
        return 0.0

    embeddings = model.encode([resume_text, jd_text], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()

    clamped = max(0.0, min(1.0, similarity))
    return round(clamped * 100, 1)


def missing_skills(resume_skills: list[str], jd_text: str) -> list[str]:
    """Skills required by the JD that are absent from the resume.

    Extracts known skills from ``jd_text`` (reusing the same PhraseMatcher as
    resume parsing) and returns those not present in ``resume_skills``.
    """
    jd_skills = extract_skills(jd_text)
    have = {skill.lower() for skill in resume_skills}
    return [skill for skill in jd_skills if skill.lower() not in have]
