"""Standalone Streamlit app (single-service deployment).

Runs the full analysis pipeline **in-process** — it imports the same NLP core
the FastAPI backend uses (``app.parser`` / ``app.skills`` / ``app.matcher`` /
``app.suggestions``) and calls it directly, no HTTP round-trip. That makes it
deployable as one free service (Streamlit Community Cloud) with no separate
backend to host.

The two-tier version (Streamlit UI -> FastAPI over HTTP) lives in
``frontend/app.py`` for local/Docker use; this file is the cloud-demo entrypoint.
"""

from html import escape

import streamlit as st

from app.matcher import match_score, missing_skills
from app.parser import extract_text
from app.skills import extract_skills_and_entities
from app.suggestions import generate_suggestions

# --------------------------------------------------------------------------- #
# Page config + styling
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      #MainMenu, footer {visibility: hidden;}
      .block-container {padding-top: 2.4rem; max-width: 1180px;}

      .app-header {border-bottom: 1px solid #E5E7EB; padding-bottom: 1.1rem; margin-bottom: 1.6rem;}
      .app-header .eyebrow {
        font-size: .72rem; letter-spacing: .14em; text-transform: uppercase;
        color: #2563EB; font-weight: 700;
      }
      .app-header h1 {font-size: 1.85rem; font-weight: 700; margin: .35rem 0 .3rem; color: #0F172A;}
      .app-header p  {color: #475569; margin: 0; font-size: 1rem; max-width: 760px;}

      .label {
        font-size: .72rem; letter-spacing: .09em; text-transform: uppercase;
        color: #64748B; font-weight: 700; margin-bottom: .55rem;
      }
      .card {
        border: 1px solid #E5E7EB; border-radius: 10px; background: #fff;
        padding: 1.15rem 1.3rem; margin-bottom: 1rem;
      }
      .muted {color: #94A3B8; font-size: .88rem;}

      .tag {
        display: inline-block; padding: 4px 11px; margin: 0 5px 7px 0;
        border-radius: 6px; font-size: .82rem; font-weight: 500; border: 1px solid;
      }
      .tag-skill   {background:#EFF5FF; color:#1D4ED8; border-color:#D5E3FF;}
      .tag-missing {background:#FEF2F2; color:#B91C1C; border-color:#FBD3D3;}
      .tag-entity  {background:#F8FAFC; color:#334155; border-color:#E5E7EB;}

      .meter {height: 8px; background: #F1F5F9; border-radius: 6px; overflow: hidden; margin: .55rem 0 .45rem;}
      .meter > div {height: 100%; border-radius: 6px;}

      .ent-grid {display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1.2rem;}
      .ent-h {font-size: .82rem; font-weight: 700; color: #0F172A; margin-bottom: .5rem;}

      .sug {padding: .55rem 0; border-bottom: 1px solid #F1F5F9; color: #334155; font-size: .93rem;}
      .sug:last-child {border-bottom: 0;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def tags_html(items, kind: str) -> str:
    if not items:
        return '<span class="muted">None found.</span>'
    return "".join(f'<span class="tag tag-{kind}">{escape(str(i))}</span>' for i in items)


def score_meta(score: float):
    """Return (label, color) for a 0-100 match score."""
    if score >= 70:
        return "Strong match", "#15803D"
    if score >= 40:
        return "Moderate match", "#B45309"
    return "Weak match", "#B91C1C"


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("**Resume Analyzer**")
    st.markdown(
        '<span class="muted">Skill extraction, named-entity recognition, and '
        "semantic job matching for resumes.</span>",
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown('<div class="label">Methodology</div>', unsafe_allow_html=True)
    st.markdown(
        "- **Skills** — spaCy PhraseMatcher\n"
        "- **Entities** — spaCy named-entity recognition\n"
        "- **Job match** — sentence-transformer embeddings, cosine similarity\n"
        "- **Feedback** — rule-based checks"
    )
    st.divider()
    st.caption("FastAPI · spaCy · sentence-transformers · Streamlit")
    st.link_button("View source on GitHub", "https://github.com/mahim83/resume-analyzer")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="app-header">
      <div class="eyebrow">NLP Resume Analysis</div>
      <h1>Resume Analyzer</h1>
      <p>Extract skills and key entities from a resume, and measure how closely
      it matches a job description — with the specific skills it's missing.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
left, right = st.columns([1, 1], gap="large")
with left:
    st.markdown('<div class="label">Resume &nbsp;·&nbsp; PDF or DOCX</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Resume", type=["pdf", "docx"], label_visibility="collapsed")
with right:
    st.markdown('<div class="label">Job description &nbsp;·&nbsp; optional</div>', unsafe_allow_html=True)
    jd_text = st.text_area(
        "Job description",
        height=138,
        placeholder="Paste a job description to compute a match score and identify missing skills…",
        label_visibility="collapsed",
    )

analyze = st.button("Analyze resume", type="primary")

st.markdown("<div style='margin:.4rem 0 1.2rem'></div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
if not analyze:
    st.markdown(
        '<span class="muted">Upload a resume and select <b>Analyze resume</b> to '
        "view extracted skills, entities, a job-match score, and suggestions.</span>",
        unsafe_allow_html=True,
    )
    st.stop()

if uploaded_file is None:
    st.warning("Please upload a resume first.")
    st.stop()

# --- Parse ---
try:
    text = extract_text(uploaded_file.getvalue(), uploaded_file.name)
except ValueError as exc:
    st.error(f"Could not read the file: {exc}")
    st.stop()

# --- Skills + entities ---
with st.spinner("Extracting skills and entities…"):
    extracted = extract_skills_and_entities(text)
skills = extracted["skills"]
entities = extracted["entities"]

# --- Optional JD match ---
score = None
missing = []
if jd_text.strip():
    with st.spinner("Computing semantic match score…"):
        score = match_score(text, jd_text)
        missing = missing_skills(skills, jd_text)

# --- Summary metrics ---
m1, m2, m3 = st.columns(3)
m1.metric("Skills found", len(skills))
m2.metric("Entities detected", sum(len(v) for v in entities.values()))
m3.metric("Match score", f"{score}%" if score is not None else "—")

st.markdown("<div style='margin:.5rem 0'></div>", unsafe_allow_html=True)

# --- Match score card ---
if score is not None:
    label, color = score_meta(score)
    width = max(min(score, 100), 2)
    st.markdown(
        f"""
        <div class="card">
          <div class="label">Job Match Score</div>
          <div style="display:flex; align-items:baseline; gap:.7rem;">
            <span style="font-size:2rem; font-weight:700; color:{color}; line-height:1">{score}%</span>
            <span style="color:{color}; font-weight:600; font-size:.95rem">{label}</span>
          </div>
          <div class="meter"><div style="width:{width}%; background:{color}"></div></div>
          <span class="muted">Semantic similarity between the resume and the job description.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Skills + missing ---
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown(
        f'<div class="card"><div class="label">Skills Found</div>{tags_html(skills, "skill")}</div>',
        unsafe_allow_html=True,
    )
with c2:
    body = tags_html(missing, "missing") if jd_text.strip() else \
        '<span class="muted">Add a job description to identify missing skills.</span>'
    st.markdown(
        f'<div class="card"><div class="label">Missing Skills</div>{body}</div>',
        unsafe_allow_html=True,
    )

# --- Entities ---
if any(entities.values()):
    groups = [("People", "PERSON"), ("Organizations", "ORG"), ("Dates", "DATE")]
    cells = "".join(
        f'<div><div class="ent-h">{name}</div>{tags_html(entities.get(key, []), "entity")}</div>'
        for name, key in groups
    )
    st.markdown(
        f'<div class="card"><div class="label">Extracted Entities</div>'
        f'<div class="ent-grid">{cells}</div></div>',
        unsafe_allow_html=True,
    )

# --- Suggestions ---
suggestions = generate_suggestions(text)
if suggestions:
    rows = "".join(f'<div class="sug">{escape(tip)}</div>' for tip in suggestions)
    st.markdown(
        f'<div class="card"><div class="label">Suggestions</div>{rows}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="card"><div class="label">Suggestions</div>'
        '<span style="color:#15803D; font-weight:600;">Resume passed all basic checks.</span></div>',
        unsafe_allow_html=True,
    )
