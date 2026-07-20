"""Streamlit frontend for the Resume Analyzer."""

import os

import requests
import streamlit as st

# Point this at the deployed backend by setting BACKEND_URL in the environment.
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Resume Analyzer", page_icon="📄", layout="centered")

st.title("📄 Resume Analyzer")
st.caption(
    "Upload a resume to extract skills and entities. Optionally paste a job "
    "description to get a semantic match score and see which required skills "
    "are missing."
)

uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
jd_text = st.text_area(
    "Job description (optional)",
    height=180,
    placeholder="Paste a job description here to compute a match score...",
)

analyze_clicked = st.button("Analyze", type="primary", use_container_width=True)


def _analyze(file, job_description: str) -> dict:
    """Call the backend /analyze endpoint and return the parsed JSON."""
    files = {"file": (file.name, file.getvalue())}
    data = {"jd_text": job_description} if job_description.strip() else {}
    response = requests.post(
        f"{BACKEND_URL}/analyze", files=files, data=data, timeout=120
    )
    response.raise_for_status()
    return response.json()


if analyze_clicked:
    if uploaded_file is None:
        st.warning("Please upload a resume first.")
    else:
        with st.spinner("Analyzing resume..."):
            try:
                result = _analyze(uploaded_file, jd_text)
            except requests.exceptions.HTTPError as exc:
                detail = ""
                try:
                    detail = exc.response.json().get("detail", "")
                except Exception:
                    detail = exc.response.text
                st.error(f"Analysis failed ({exc.response.status_code}): {detail}")
                result = None
            except requests.exceptions.RequestException as exc:
                st.error(f"Could not reach the backend at {BACKEND_URL}: {exc}")
                result = None

        if result:
            # --- Match score (only when a JD was provided) ---------------
            score = result.get("match_score")
            if score is not None:
                st.subheader("Job Match Score")
                st.metric("Semantic similarity", f"{score}%")
                st.progress(min(int(score), 100))

            # --- Skills found -------------------------------------------
            st.subheader("Skills Found")
            skills = result.get("skills_found", [])
            if skills:
                st.markdown(" ".join(f"`{skill}`" for skill in skills))
            else:
                st.write("No known skills detected.")

            # --- Missing skills -----------------------------------------
            missing = result.get("missing_skills", [])
            if missing:
                st.subheader("Missing Skills (from the job description)")
                for skill in missing:
                    st.markdown(f"- {skill}")

            # --- Entities -----------------------------------------------
            entities = result.get("entities", {})
            if any(entities.values()):
                st.subheader("Extracted Entities")
                for label, values in entities.items():
                    if values:
                        st.markdown(f"**{label}:** {', '.join(values)}")

            # --- Suggestions --------------------------------------------
            suggestions = result.get("suggestions", [])
            st.subheader("Suggestions")
            if suggestions:
                for tip in suggestions:
                    st.markdown(f"- {tip}")
            else:
                st.write("No suggestions — your resume passed the basic checks. ✅")

st.divider()
st.caption(f"Backend: {BACKEND_URL}")
