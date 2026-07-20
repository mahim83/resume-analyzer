<div align="center">

# 📄 Resume Analyzer

**Extract skills & entities from a resume, and semantically match it against any job description — powered by NLP.**

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://resume-analyzer-mahim.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![spaCy](https://img.shields.io/badge/spaCy-NLP-09A3D5?logo=spacy&logoColor=white)](https://spacy.io/)
[![Tests](https://img.shields.io/badge/tests-27_passing-brightgreen)](tests/)

</div>

---

## Overview

**Resume Analyzer** reads a resume (PDF or DOCX), uses **Natural Language Processing** to pull out the candidate's skills and key entities, and — given a job description — computes a **semantic match score** and lists the required skills the resume is missing, plus quick rule-based writing feedback.

It's the core idea behind an Applicant Tracking System (ATS), but **explainable**: instead of opaque keyword counting, it uses token-level phrase matching for skills and sentence embeddings for *meaning-based* job matching.

> 🔗 **Live demo:** https://resume-analyzer-mahim.streamlit.app/

---

## ✨ Features

- 📄 **PDF & DOCX parsing** — extracts clean text from either format.
- 🧠 **Skill extraction** — matches ~330 curated skills (languages, frameworks, databases, cloud, DevOps, ML, and soft skills) with a case-insensitive, multi-word phrase matcher.
- 🏷️ **Entity recognition** — pulls out people, organizations, and dates via spaCy NER.
- 🎯 **Semantic job matching** — cosine similarity over sentence embeddings gives a 0–100 match score that captures *meaning*, not just keyword overlap.
- ➖ **Missing-skills detection** — shows which skills the job asks for that the resume lacks.
- 💡 **Writing suggestions** — flags a too-short resume, missing metrics, and weak passive phrasing.
- ⚡ **REST API + Web UI** — a documented FastAPI backend *and* an interactive Streamlit frontend.

---

## 🎯 How the NLP works

| Task | Technique | Why this choice |
|---|---|---|
| **Skills** | spaCy **`PhraseMatcher`** (`attr="LOWER"`) | Token-level & case-insensitive, so multi-word skills like *"machine learning"* match cleanly — no brittle regex boundaries, and it scales to hundreds of terms. |
| **Entities** | spaCy **NER** (PERSON / ORG / DATE) | A pretrained statistical model generalizes to names & companies a keyword list never could. |
| **Job match** | **sentence-transformers** (`all-MiniLM-L6-v2`) + cosine similarity | Embeddings capture *semantic* similarity — a resume that says "built REST services in Python" matches a JD wanting "backend API development" even without shared words. MiniLM is small (~80 MB) yet strong. |

> ⚙️ **Performance detail:** ML models are loaded **once** (spaCy at import, the transformer lazily on first use) — never per request — so responses stay fast.

---

## 🏗️ Architecture

```
        User (browser)
             │  uploads resume + pastes job description
             ▼
   ┌────────────────────┐        ┌─────────────────────┐
   │   Streamlit UI     │   or   │   Streamlit UI      │
   │ (in-process mode)  │        │ → FastAPI over HTTP  │
   └────────────────────┘        └─────────────────────┘
             │
             ▼
   ┌───────────────────────────────────────────────────┐
   │                 NLP Core  (app/)                   │
   │  parser.py      PDF/DOCX  →  text                  │
   │  skills.py      PhraseMatcher skills + NER entities│
   │  matcher.py     embeddings → match score + missing │
   │  suggestions.py rule-based feedback                │
   │  models.py      Pydantic schema → JSON             │
   └───────────────────────────────────────────────────┘
```

The same NLP core is exposed **two ways**: a **FastAPI REST API** (`/analyze` + Swagger at `/docs`) and a **standalone Streamlit app** that calls it in-process.

---

## 🧰 Tech Stack

**Language:** Python 3.11+
**NLP/ML:** spaCy (`en_core_web_sm`), sentence-transformers (`all-MiniLM-L6-v2`), PyTorch
**Parsing:** pdfplumber, python-docx
**Backend:** FastAPI, Uvicorn, Pydantic
**Frontend:** Streamlit
**Testing:** pytest
**Deploy:** Docker · Streamlit Community Cloud · (Render blueprint included)

---

## 📡 API Reference

### `POST /analyze`
Multipart form:

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | Resume as `.pdf` or `.docx` |
| `jd_text` | string | ❌ | Job description to match against |

**Response** (`AnalysisResult`):
```json
{
  "skills_found": ["python", "fastapi", "docker"],
  "entities": { "PERSON": ["Jane Doe"], "ORG": ["Acme Corporation"], "DATE": ["2021"] },
  "match_score": 70.3,
  "missing_skills": ["graphql", "redis"],
  "suggestions": ["Consider quantifying achievements with numbers or metrics."]
}
```

**Errors:** `415` (unsupported file type) · `422` (unparseable/empty file).
Interactive docs auto-generated at **`/docs`**.

---

## 🛠️ Getting Started (local)

```bash
# 1. Clone
git clone https://github.com/mahim83/resume-analyzer.git
cd resume-analyzer

# 2. Create a virtual environment
python -m venv .venv
# Windows:  .venv\Scripts\activate     |  macOS/Linux:  source .venv/bin/activate

# 3. Install (the spaCy model installs via requirements.txt)
pip install -r requirements.txt
```

**Run the standalone Streamlit app (simplest):**
```bash
streamlit run streamlit_app.py            # http://localhost:8501
```

**Or run the two-tier setup (FastAPI + Streamlit frontend):**
```bash
uvicorn app.main:app --reload             # backend  → http://localhost:8000/docs
streamlit run frontend/app.py             # frontend → http://localhost:8501
```

**Quick API smoke test:**
```bash
curl -F "file=@resume.pdf" \
     -F "jd_text=Backend engineer with Python, Docker, AWS." \
     http://localhost:8000/analyze
```

---

## 🧪 Tests

```bash
pip install -r requirements-dev.txt
pytest
```

**27 tests** cover PDF/DOCX parsing (incl. corrupt/unsupported → 415/422), skill & entity extraction, semantic match scoring, missing-skills detection, all suggestion rules, and the `/analyze` API end-to-end. Sample fixtures live in `tests/fixtures/`.

---

## 🐳 Docker

```bash
docker build -t resume-analyzer .
docker run -p 8000:8000 resume-analyzer   # http://localhost:8000/docs
```
The image bakes in the sentence-transformer at build time, so startup needs no network and the first request is fast.

---

## ☁️ Deployment

**Single service (used for the live demo):** `streamlit_app.py` runs the whole pipeline **in-process**, so it deploys as one free app on **Streamlit Community Cloud** — point it at this repo with `streamlit_app.py` as the main file.

**Two-tier (microservice):** deploy the FastAPI Docker image on any container host, then the Streamlit frontend with `BACKEND_URL` pointing at it.

> 💡 **Memory note:** The transformer is torch-backed and memory-heavy. It's lazy-loaded so startup stays light, but the match step needs a host with **≥ 1 GB RAM** (a 512 MB free tier will OOM). Streamlit Community Cloud (~1 GB) and Hugging Face Spaces (16 GB free) both work.

---

## 📁 Project Structure

```
resume-analyzer/
├── app/
│   ├── main.py            FastAPI app + /analyze endpoint
│   ├── parser.py          PDF/DOCX text extraction
│   ├── skills.py          PhraseMatcher skills + spaCy NER entities
│   ├── matcher.py         sentence-transformers match score + missing skills
│   ├── suggestions.py     rule-based writing feedback
│   ├── models.py          Pydantic response schema
│   └── skills_list.json   ~330 skill terms
├── frontend/
│   └── app.py             Streamlit UI (calls FastAPI over HTTP)
├── streamlit_app.py       Standalone Streamlit UI (runs the pipeline in-process)
├── tests/                 27 pytest tests + sample fixtures
├── Dockerfile
├── render.yaml
├── requirements.txt
└── requirements-dev.txt
```

---

## 🔮 Roadmap (with more time)

- 🎯 Fine-tune a **NER model on labeled resume data** (the general model occasionally mislabels tech terms like "Docker" as a PERSON/ORG).
- 📑 **Section-aware parsing** (Experience / Education / Skills) for more precise, scoped extraction.
- 📊 A **labeled evaluation set** with precision/recall instead of eyeballed checks.
- 🗂️ A maintained **skill taxonomy** with synonyms (e.g. "js" ↔ "javascript", "k8s" ↔ "kubernetes").

---

## 📝 License

Released under the **MIT License** — see [`LICENSE`](LICENSE).

<div align="center">

Built with FastAPI, spaCy & sentence-transformers.

</div>
