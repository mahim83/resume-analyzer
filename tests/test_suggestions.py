"""Tests for app.suggestions — rule-based feedback (no ML deps)."""

from app.suggestions import generate_suggestions


def test_short_passive_no_digits_triggers_all_three():
    tips = generate_suggestions("I was responsible for things.")
    assert len(tips) == 3
    assert any("too short" in t for t in tips)
    assert any("quantifying" in t for t in tips)
    assert any("responsible for" in t for t in tips)


def test_digits_suppress_quantify_tip():
    tips = generate_suggestions("Improved latency by 40% across 3 services.")
    assert not any("quantifying" in t for t in tips)


def test_clean_long_resume_has_no_short_flag():
    text = "word " * 250 + "we built 5 systems and led 3 teams."
    tips = generate_suggestions(text)
    assert not any("too short" in t for t in tips)


def test_returns_list_of_strings():
    tips = generate_suggestions("hello world")
    assert isinstance(tips, list)
    assert all(isinstance(t, str) for t in tips)
