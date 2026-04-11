from my_support_agent.phone_utils import normalize_phone


def test_already_normalized():
    assert normalize_phone("09123456789") == "09123456789"


def test_strip_dashes():
    assert normalize_phone("09-123-456-789") == "09123456789"


def test_strip_spaces():
    assert normalize_phone("09 123 456 789") == "09123456789"


def test_plus95_prefix():
    assert normalize_phone("+95 9 123 456 789") == "09123456789"


def test_959_prefix():
    assert normalize_phone("959123456789") == "09123456789"


def test_strip_parentheses():
    assert normalize_phone("(09) 123-456-789") == "09123456789"


def test_invalid_too_short():
    assert normalize_phone("0912") is None


def test_invalid_wrong_prefix():
    assert normalize_phone("12345678901") is None


def test_empty_string():
    assert normalize_phone("") is None


def test_none_input():
    assert normalize_phone(None) is None
