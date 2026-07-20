"""Skill and entity extraction using spaCy PhraseMatcher + NER.

The spaCy model and PhraseMatcher are built once at import time so that a
request handler never pays model-load or matcher-build cost.
"""

import json
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher

# --- One-time, module-level setup ------------------------------------------

_SKILLS_PATH = Path(__file__).parent / "skills_list.json"

with _SKILLS_PATH.open(encoding="utf-8") as f:
    SKILLS: list[str] = json.load(f)

# We only need the tagger/parser off for speed; NER stays on because we use it.
nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer"])

# attr="LOWER" makes matching case-insensitive at the token level, which also
# handles multi-word skills like "machine learning" or "spring boot" cleanly.
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
for _skill in SKILLS:
    # Use the tokenizer-only pipeline to build patterns quickly, and register
    # each pattern under the canonical skill string so we can recover it later.
    matcher.add(_skill, [nlp.make_doc(_skill)])

# Entity labels we surface to the user.
_ENTITY_LABELS = ("PERSON", "ORG", "DATE")


# --- Helpers ----------------------------------------------------------------

def extract_skills(text: str) -> list[str]:
    """Return the sorted, de-duplicated list of known skills found in ``text``.

    Only the PhraseMatcher runs here (NER is skipped), making this cheap enough
    to reuse for job-description parsing.
    """
    doc = nlp.make_doc(text)
    matches = matcher(doc)
    found = {nlp.vocab.strings[match_id] for match_id, _start, _end in matches}
    return sorted(found)


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    """De-duplicate case-insensitively while keeping first-seen surface form."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def extract_skills_and_entities(text: str) -> dict:
    """Extract known skills and named entities from resume ``text``.

    Returns::

        {
            "skills": ["python", "sql", ...],
            "entities": {"PERSON": [...], "ORG": [...], "DATE": [...]},
        }
    """
    doc = nlp(text)

    # Skills via PhraseMatcher over the full Doc.
    skills = sorted(
        {nlp.vocab.strings[match_id] for match_id, _s, _e in matcher(doc)}
    )

    # Entities via standard spaCy NER, bucketed by label.
    buckets: dict[str, list[str]] = {label: [] for label in _ENTITY_LABELS}
    for ent in doc.ents:
        if ent.label_ in buckets:
            buckets[ent.label_].append(ent.text)

    entities = {label: _dedupe_preserve_order(values) for label, values in buckets.items()}

    return {"skills": skills, "entities": entities}
