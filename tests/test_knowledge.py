from my_support_agent.tools.knowledge import _search_sections


SAMPLE_KB = """## Payment Methods

We accept MMQR and bank transfer.

## JLPT Levels

N5 is beginner. N1 is advanced.

## Refund Policy

Full refund before class starts.
"""


def test_search_finds_matching_section():
    results = _search_sections(SAMPLE_KB, "payment")
    assert len(results) == 1
    assert "MMQR" in results[0]


def test_search_finds_multiple_sections():
    results = _search_sections(SAMPLE_KB, "JLPT levels")
    assert len(results) >= 1
    assert any("N5" in r for r in results)


def test_search_case_insensitive():
    results = _search_sections(SAMPLE_KB, "REFUND")
    assert len(results) == 1
    assert "refund" in results[0].lower()


def test_search_no_match():
    results = _search_sections(SAMPLE_KB, "telegram")
    assert len(results) == 0


def test_search_empty_query():
    results = _search_sections(SAMPLE_KB, "")
    assert len(results) == 0


def test_search_none_kb():
    results = _search_sections(None, "payment")
    assert len(results) == 0
