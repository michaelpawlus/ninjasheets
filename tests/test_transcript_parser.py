from ninjasheets.config import load_patterns
from ninjasheets.parsing import extract_candidates
from ninjasheets.transcript import TranscriptLine, normalize_text


def _line(t, text):
    return TranscriptLine("vid", t, 2.0, text, normalize_text(text))


def test_normalize_drops_noise():
    assert normalize_text(">> Our next [music] competitor") == "Our next competitor"


def test_extracts_announcement_with_gym_and_location():
    lines = [
        _line(100, "Our next competitor is Alex Sample."),
        _line(103, "Alex is from Springfield, New Jersey at age 11."),
        _line(106, "She is representing Example Ninja today."),
    ]
    cands = extract_candidates(lines, load_patterns())
    assert len(cands) == 1
    c = cands[0]
    assert c.athlete_name_clean == "Alex Sample"
    assert c.gym_raw == "Example Ninja"
    assert (c.city, c.state) == ("Springfield", "New Jersey")
    assert c.confidence == "high"


def test_dedupes_repeated_mentions():
    lines = [
        _line(100, "Our next competitor is Quinn."),
        _line(110, "Our next competitor is Quinn again."),
        _line(400, "Our next competitor is Quinn."),  # far apart -> distinct
    ]
    cands = extract_candidates(lines, load_patterns())
    names = [c.athlete_name_clean for c in cands]
    assert names.count("Quinn") == 2


def test_does_not_match_commentary():
    lines = [_line(10, "She is flying through the course right now.")]
    assert extract_candidates(lines, load_patterns()) == []
