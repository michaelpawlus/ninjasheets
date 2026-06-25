from ninjasheets.utils import apply_timestamp_buffer, hhmmss, youtube_run_url


def test_hhmmss_basic():
    assert hhmmss(3725) == "01:02:05"
    assert hhmmss(0) == "00:00:00"
    assert hhmmss(59) == "00:00:59"
    assert hhmmss(61) == "00:01:01"


def test_buffer_never_negative():
    assert apply_timestamp_buffer(3, 5) == 0
    assert apply_timestamp_buffer(125, 5) == 120


def test_run_url():
    assert youtube_run_url("abc123", 90) == "https://youtu.be/abc123?t=90"
