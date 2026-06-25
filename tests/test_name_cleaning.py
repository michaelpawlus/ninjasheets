from ninjasheets.config import load_patterns
from ninjasheets.parsing import _is_valid_name, clean_name

P = load_patterns()


def test_strips_leading_filler():
    assert clean_name("is Jordan", P) == "Jordan"
    assert clean_name("new Quinn", P) == "Quinn"


def test_titlecases_lowercase_tokens():
    assert clean_name("jordan", P) == "Jordan"
    assert clean_name("alex sample", P) == "Alex Sample"


def test_preserves_mixed_case():
    assert clean_name("Robin McSample", P) == "Robin McSample"


def test_stopwords_rejected():
    assert not _is_valid_name("She", P)
    assert not _is_valid_name("Is", P)
    assert _is_valid_name("Quinn", P)
    assert _is_valid_name("Robin Sample", P)
