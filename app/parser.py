"""Document parsing: extract raw text from PDF or DOCX resume files."""

import io

import pdfplumber
from docx import Document


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from every page of a PDF, joined with newlines."""
    pages = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)
    return "\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from all paragraphs of a DOCX, joined with newlines."""
    document = Document(io.BytesIO(file_bytes))
    paragraphs = [para.text for para in document.paragraphs]
    return "\n".join(paragraphs)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract raw text from a PDF or DOCX file.

    Determines the file type from the filename extension. Raises
    ``ValueError`` on an unsupported type or when extraction yields no
    (non-whitespace) text.
    """
    name = (filename or "").lower().strip()

    if name.endswith(".pdf"):
        extractor = _extract_pdf
    elif name.endswith(".docx"):
        extractor = _extract_docx
    else:
        raise ValueError(
            f"Unsupported file type: '{filename}'. Only .pdf and .docx are supported."
        )

    # Convert library-specific failures (corrupt/empty/password-protected file,
    # bad zip, etc.) into ValueError so the API can report a clean 422.
    try:
        text = extractor(file_bytes)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Could not read the {name.rsplit('.', 1)[-1].upper()} file. "
            "It may be corrupt, empty, or password-protected."
        ) from exc

    if not text or not text.strip():
        raise ValueError(
            "No text could be extracted from the document. "
            "It may be empty, image-only, or scanned."
        )

    return text
