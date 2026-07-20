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
      /* Hide default Streamlit chrome for a cleaner demo */
      #MainMenu, footer {visibility: hidden;}

      .hero {
        background: linear-gradient(120deg, #6366F1 0%, #8B5CF6 55%, #EC4899 100%);
        padding: 2.1rem 2.4rem; border-radius: 18px; color: #fff;
        margin-bottom: 1.4rem; box-shadow: 0 10px 30px rgba(99,102,241,0.25);
      }
      .hero h1 {margin: 0; font-size: 2.15rem; font-weight: 800; letter-spacing: -0.5px;}
      .hero p  {margin: .5rem 0 0; font-size: 1.02rem; opacity: .95; max-width: 720px;}

      .chip {
        display: inline-block; padding: 5px 13px; margin: 4px 4px 4px 0;
        border-radius: 20px; font-size: .84rem; font-weight: 600; line-height: 1.4;
      }
      .chip-skill   {background:#EAF7EE; color:#1E7B44; border:1px solid #B6E3C6;}
      .chip-missing {background:#FDECEC; color:#C0322B; border:1px solid #F4B9B5;}
      .chip-entity  {background:#EEF0FE; color:#4746C9; border:1px solid #C7C9F7;}

      .card {
        background:#fff; border:1px solid #ECEDF5; border-radius:14px;
        padding:1.1rem 1.25rem; margin-bottom:1rem;
        box-shadow:0 2px 10px rgba(31,34,51,0.04);
      }
      .card h4 {margin:0 0 .6rem; font-size:1.02rem; color:#1F2233;}
      .muted {color:#8A8FA3; font-size:.9rem;}

      .score-wrap {height:14px; background:#EEEFF6; border-radius:10px; overflow:hidden; margin:.35rem 0 .2rem;}
      .score-bar  {height:100%; border-radius:10px;}

      .stButton>button {
        border-radius:10px; font-weight:700; padding:.55rem 0;
        background:linear-gradient(120deg,#6366F1,#8B5CF6); color:#fff; border:0;
      }
      .stButton>button:hover {filter:brightness(1.05);}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def render_chips(items, kind):
    if not items:
        st.markdown('<span class="muted">None found.</span>', unsafe_allow_html=True)
        return
    html = "".join(f'<span class="chip chip-{kind}">{escape(str(i))}</span>' for i in items)
    st.markdown(html, unsafe_allow_html=True)


def score_meta(score: float):
    """Return (label, color) for a 0-100 match score."""
    if score >= 70:
        return "Strong match", "#1E7B44"
    if score >= 40:
        return "Moderate match", "#B9770B"
    return "Weak match", "#C0322B"


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.markdown("### 📄 Resume Analyzer")
    st.markdown(
        "Extract skills & entities from a resume and semantically match it "
        "against a job description."
    )
    st.divider()
    st.markdown("#### How it works")
    st.markdown(
        "- **Skills** — spaCy `PhraseMatcher`\n"
        "- **Entities** — spaCy NER (people / orgs / dates)\n"
        "- **Job match** — sentence-transformer embeddings + cosine similarity\n"
        "- **Feedback** — rule-based suggestions"
    )
    st.divider()
    st.caption("Built with FastAPI · spaCy · sentence-transformers · Streamlit")
    st.link_button("⭐ View source on GitHub", "https://github.com/mahim83/resume-analyzer")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <div class="hero">
      <h1>📄 Resume Analyzer</h1>
      <p>Upload a resume to extract skills and key details. Add a job description
      to get a semantic match score and see exactly which required skills you're
      missing — powered by NLP.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
left, right = st.columns([1, 1], gap="large")
with left:
    st.markdown("#### 1&nbsp;&nbsp;Upload your resume")
    uploaded_file = st.file_uploader("PDF or DOCX", type=["pdf", "docx"], label_visibility="collapsed")
with right:
    st.markdown("#### 2&nbsp;&nbsp;Paste a job description *(optional)*")
    jd_text = st.text_area(
        "Job description",
        height=150,
        placeholder="Paste a job description to compute a match score and find missing skills...",
        label_visibility="collapsed",
    )

analyze = st.button("🔍  Analyze Resume", type="primary", use_container_width=True)

st.divider()


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
if not analyze:
    st.info("👆 Upload a resume and click **Analyze** to see extracted skills, entities, a job-match score, and suggestions.")
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
with st.spinner("Extracting skills and entities..."):
    extracted = extract_skills_and_entities(text)
skills = extracted["skills"]
entities = extracted["entities"]

# --- Optional JD match ---
score = None
missing = []
if jd_text.strip():
    with st.spinner("Computing semantic match score..."):
        score = match_score(text, jd_text)
        missing = missing_skills(skills, jd_text)

# --- Summary metrics ---
m1, m2, m3 = st.columns(3)
m1.metric("🧠 Skills found", len(skills))
m2.metric("🏷️ Entities", sum(len(v) for v in entities.values()))
m3.metric("🎯 Match score", f"{score}%" if score is not None else "—")

# --- Match score card ---
if score is not None:
    label, color = score_meta(score)
    st.markdown(
        f"""
        <div class="card">
          <h4>Job Match Score &nbsp;·&nbsp; <span style="color:{color}">{label}</span></h4>
          <div style="font-size:2rem;font-weight:800;color:{color};line-height:1">{score}%</div>
          <div class="score-wrap"><div class="score-bar" style="width:{max(min(score,100),2)}%;
               background:linear-gradient(90deg,{color},{color}CC)"></div></div>
          <span class="muted">Semantic similarity between your resume and the job description.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Skills + missing side by side ---
c1, c2 = st.columns(2, gap="large")
with c1:
    st.markdown('<div class="card"><h4>✅ Skills Found</h4>', unsafe_allow_html=True)
    render_chips(skills, "skill")
    st.markdown("</div>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="card"><h4>⚠️ Missing Skills (from the job description)</h4>', unsafe_allow_html=True)
    if jd_text.strip():
        render_chips(missing, "missing")
    else:
        st.markdown('<span class="muted">Add a job description to see missing skills.</span>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- Entities ---
if any(entities.values()):
    st.markdown('<div class="card"><h4>🏷️ Extracted Entities</h4>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    labels = {"PERSON": "👤 People", "ORG": "🏢 Organizations", "DATE": "📅 Dates"}
    for col, key in zip((e1, e2, e3), ("PERSON", "ORG", "DATE")):
        with col:
            st.markdown(f"**{labels[key]}**")
            render_chips(entities.get(key, []), "entity")
    st.markdown("</div>", unsafe_allow_html=True)

# --- Suggestions ---
suggestions = generate_suggestions(text)
st.markdown('<div class="card"><h4>💡 Suggestions</h4></div>', unsafe_allow_html=True)
if suggestions:
    for tip in suggestions:
        st.warning(tip)
else:
    st.success("Your resume passed all the basic checks. ✅")
