# Resume Analyzer

Upload a resume (PDF or DOCX) and get back the technical & soft skills it
contains, the named entities in it (people, organizations, dates), and — if you
paste a job description — a **semantic match score** plus the required skills
your resume is missing. A small rule-based layer adds quick writing feedback.

The point of the project is the **NLP pipeline**: skills are pulled with a
spaCy `PhraseMatcher`, entities with spaCy NER, and job-description matching
uses sentence-transformer embeddings with cosine similarity.

## Architecture

```
Streamlit UI  ──HTTP──▶  FastAPI /analyze
                            │
                            ├─ parser.py       PDF/DOCX → text (pdfplumber / python-docx)
                            ├─ skills.py       spaCy PhraseMatcher (skills) + NER (entities)
                            ├─ matcher.py      sentence-transformers embeddings → cosine similarity
                            ├─ suggestions.py  rule-based writing feedback
                            └─ models.py       Pydantic response  →  JSON
```

## Tech choices (and why)

- **spaCy `PhraseMatcher` over regex** for skills — it matches at the token
  level and is case-insensitive (`attr="LOWER"`), so multi-word skills like
  *machine learning* or *spring boot* match cleanly without brittle regex
  boundaries, and matching stays fast even with a few hundred terms.
- **spaCy NER** for people / orgs / dates — a pretrained statistical model
  generalizes to names and companies a keyword list never could.
- **Cosine similarity over sentence embeddings** for JD matching — this
  captures *semantic* overlap (a resume saying "built REST services in Python"
  scores against a JD wanting "backend API development") rather than exact
  keyword overlap, which pure term matching misses.
- **`all-MiniLM-L6-v2`** — a ~80MB embedding model; small enough to deploy on a
  free tier while still producing strong semantic similarity.
- **Models loaded once at import time**, never per request — model loading is
  the expensive step; doing it at startup keeps `/analyze` fast and avoids
  timeouts on constrained hosts.

## API

`POST /analyze` (multipart form)

| field     | type            | required | notes                                  |
| --------- | --------------- | -------- | -------------------------------------- |
| `file`    | file            | yes      | `.pdf` or `.docx`                      |
| `jd_text` | string (form)   | no       | job description to match against       |

Response (`AnalysisResult`):

```json
{
  "skills_found": ["python", "fastapi", "docker"],
  "entities": { "PERSON": ["Jane Doe"], "ORG": ["Acme Corp"], "DATE": ["2021"] },
  "match_score": 72.4,
  "missing_skills": ["kubernetes", "graphql"],
  "suggestions": ["Consider quantifying achievements with numbers or metrics."]
}
```

- `415` — file is not `.pdf`/`.docx`.
- `422` — file could not be parsed (empty, image-only, or corrupt).

Interactive docs are auto-generated at `/docs`.

## Run locally

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Backend
uvicorn app.main:app --reload            # http://localhost:8000/docs

# Frontend (separate terminal)
streamlit run frontend/app.py            # http://localhost:8501
```

Point the frontend at a remote backend with an env var:

```bash
BACKEND_URL="https://your-backend.onrender.com" streamlit run frontend/app.py
```

Quick smoke test:

```bash
curl -F "file=@resume.pdf" http://localhost:8000/analyze
curl -F "file=@resume.pdf" -F "jd_text=We need a Python backend engineer with Docker and AWS." \
     http://localhost:8000/analyze
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

27 tests cover parsing (PDF/DOCX + error paths), skill/entity extraction, JD
match scoring, suggestions, and the `/analyze` API (including 415/422 handling).
Sample resume fixtures live in `tests/fixtures/`.

## Run with Docker

```bash
docker build -t resume-analyzer .
docker run -p 8000:8000 resume-analyzer     # http://localhost:8000/docs
```

The image pre-downloads both models at build time, so the container starts
without network access and the first request is fast.

## Deploy

**Backend (Render, Docker):** push to GitHub → New Web Service → environment
*Docker* (the `Dockerfile` / `render.yaml` blueprint are auto-detected). The
free tier caps at **512MB RAM**; if the container OOMs, the sentence-transformer
is the likely culprit — switch `matcher.py` to load the model lazily on first
request instead of at import (trade-off: a slow first request).

**Frontend (Streamlit Community Cloud or Render):** deploy `frontend/app.py`
with `BACKEND_URL` set to the deployed backend URL.

## Project layout

```
app/
  main.py          FastAPI app + /analyze endpoint
  parser.py        PDF/DOCX text extraction
  skills.py        skill (PhraseMatcher) + entity (NER) extraction
  matcher.py       JD matching via sentence-transformers
  suggestions.py   rule-based feedback
  models.py        Pydantic response models
  skills_list.json ~250 skill terms
frontend/
  app.py           Streamlit UI
Dockerfile
render.yaml
requirements.txt
```

## With more time

- Fine-tune a NER model on labeled resume data (job titles, degrees, sections)
  instead of the general-purpose pretrained model.
- Section-aware parsing (split Experience / Education / Skills) so extraction
  and suggestions can be scoped per section.
- A labeled evaluation set with precision/recall for skill extraction and
  match-score calibration, rather than eyeballed spot checks.
- Expand the skills list into a maintained taxonomy with aliases/synonyms
  (e.g. "js" ↔ "javascript", "k8s" ↔ "kubernetes").
