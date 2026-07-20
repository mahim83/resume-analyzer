FROM python:3.11-slim

WORKDIR /app

# System deps: pdfplumber needs nothing extra, but keep the image lean.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download models at build time so container startup needs no network and
# the first request is fast (no cold-start model download).
RUN python -m spacy download en_core_web_sm
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app ./app

EXPOSE 8000

# Render (and most PaaS) inject $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
