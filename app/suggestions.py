"""Rule-based resume feedback."""

# Passive / weak phrases worth flagging in favour of strong action verbs.
_PASSIVE_PHRASES = ("responsible for", "duties included", "tasked with", "worked on")

_SHORT_RESUME_WORDS = 200


def generate_suggestions(text: str) -> list[str]:
    """Return simple, rule-based improvement tips for a resume.

    Each triggered rule contributes one string; the list may be empty when the
    resume passes every check.
    """
    suggestions: list[str] = []
    lower = text.lower()

    word_count = len(text.split())
    if word_count < _SHORT_RESUME_WORDS:
        suggestions.append(
            "Resume may be too short — consider expanding on your experience."
        )

    if not any(char.isdigit() for char in text):
        suggestions.append(
            "Consider quantifying achievements with numbers or metrics "
            "(e.g. 'improved performance by 30%')."
        )

    found_phrase = next((p for p in _PASSIVE_PHRASES if p in lower), None)
    if found_phrase:
        suggestions.append(
            f"Consider replacing passive phrases like '{found_phrase}' with "
            "strong action verbs (e.g. 'built', 'led', 'designed')."
        )

    return suggestions
