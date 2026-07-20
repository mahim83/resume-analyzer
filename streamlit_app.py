"""Standalone Streamlit app (single-service deployment).

This runs the full analysis pipeline **in-process** — it imports the same NLP
core the FastAPI backend uses (``app.parser`` / ``app.skills`` / ``app.matcher``
/ ``app.suggestions``) and calls it directly, with no HTTP round-trip. That
makes it deployable as one free service (e.g. Streamlit Community Cloud) with no
separate backend to host.

The two-tier version (Streamlit UI -> FastAPI over HTTP) still lives in
``frontend/app.py`` for local/Docker use; this file is the cloud-demo entrypoint.
"""

import streamlit as st

from app.matcher import match_score, missing_skills
from app.parser import extract_text
from app.skills import extract_skills_and_entities
from app.suggestions import generate_suggestions

st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="centered")

st.title("📄 Resume Analyzer")
st.caption(
    "Upload a resume to extract skills and entities. Optionally paste a job "
    "description to get a semantic match score and see which required skills "
    "are missing. Powered by spaCy (PhraseMatcher + NER) and "
    "sentence-transformers."
)

uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
jd_text = st.text_area(
    "Job description (optional)",
    height=180,
    placeholder="Paste a job description here to compute a match score...",
)

if st.button("Analyze", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please upload a resume first.")
        st.stop()

    # --- Parse ---
    try:
        text = extract_text(uploaded_file.getvalue(), uploaded_file.name)
    except ValueError as exc:
        st.error(f"Could not read the file: {exc}")
        st.stop()

    # --- Skills + entities (spaCy) ---
    with st.spinner("Extracting skills and entities..."):
        extracted = extract_skills_and_entities(text)
    skills = extracted["skills"]

    # --- Optional JD match (loads the embedding model on first use) ---
    score = None
    missing = []
    if jd_text.strip():
        with st.spinner("Computing semantic match score..."):
            score = match_score(text, jd_text)
            missing = missing_skills(skills, jd_text)

    # --- Render results ---
    if score is not None:
        st.subheader("Job Match Score")
        st.metric("Semantic similarity", f"{score}%")
        st.progress(min(int(score), 100))

    st.subheader("Skills Found")
    if skills:
        st.markdown(" ".join(f"`{s}`" for s in skills))
    else:
        st.write("No known skills detected.")

    if missing:
        st.subheader("Missing Skills (from the job description)")
        for s in missing:
            st.markdown(f"- {s}")

    entities = extracted["entities"]
    if any(entities.values()):
        st.subheader("Extracted Entities")
        for label, values in entities.items():
            if values:
                st.markdown(f"**{label}:** {', '.join(values)}")

    st.subheader("Suggestions")
    suggestions = generate_suggestions(text)
    if suggestions:
        for tip in suggestions:
            st.markdown(f"- {tip}")
    else:
        st.write("No suggestions — your resume passed the basic checks. ✅")
