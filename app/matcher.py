"""Job-description matching via sentence-transformer embeddings.

The embedding model (torch-backed) is the single largest memory allocation in
this service. On a 512MB host, importing torch + loading the model *at import
time* alongside spaCy exceeds the RAM ceiling and the container is OOM-killed
before it can even start.

To stay within that ceiling we **lazy-load**: neither torch nor the model is
touched until the first call that actually needs a match score. This keeps
startup light (spaCy + FastAPI only) so the service boots reliably, and
resume-only requests (no job description) never pay the cost at all. The model
is still baked into the Docker image at build time, so the first match request
loads from local cache rather than downloading.
"""

from .skills import extract_skills

# all-MiniLM-L6-v2 is a small (~80MB) general-purpose embedding model that
# captures semantic similarity well while staying deployable on small hosts.
_MODEL_NAME = "all-MiniLM-L6-v2"
_model = None  # populated on first use by _get_model()


def _get_model():
    """Load and cache the embedding model on first use (lazy import of torch)."""
    global _model
    if _model is None:
        # Import here, not at module top, so importing this module does not pull
        # torch into memory at app startup.
        from sentence_transformers import SentenceTransformer

        try:
            import torch

            # Keep torch's threadpool small to reduce memory/CPU on tiny hosts.
            torch.set_num_threads(1)
        except Exception:
            pass

        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def match_score(resume_text: str, jd_text: str) -> float:
    """Semantic similarity between a resume and a job description, 0-100.

    Encodes both texts, takes the cosine similarity of the embeddings, clamps
    to ``[0, 1]`` (embeddings can produce small negatives for unrelated text),
    and scales to a 0-100 score rounded to one decimal place.
    """
    if not resume_text.strip() or not jd_text.strip():
        return 0.0

    from sentence_transformers import util

    model = _get_model()
    embeddings = model.encode([resume_text, jd_text], convert_to_tensor=True)
    similarity = util.cos_sim(embeddings[0], embeddings[1]).item()

    clamped = max(0.0, min(1.0, similarity))
    return round(clamped * 100, 1)


def missing_skills(resume_skills: list[str], jd_text: str) -> list[str]:
    """Skills required by the JD that are absent from the resume.

    Extracts known skills from ``jd_text`` (reusing the same PhraseMatcher as
    resume parsing) and returns those not present in ``resume_skills``. This
    path uses only spaCy, so it stays cheap and never loads the embedding model.
    """
    jd_skills = extract_skills(jd_text)
    have = {skill.lower() for skill in resume_skills}
    return [skill for skill in jd_skills if skill.lower() not in have]
