from ninjasheets.config import VideoConfig
from ninjasheets.parsing import Candidate
from ninjasheets.pipeline import _candidate_to_run


def test_candidate_to_run_builds_link_and_buffer():
    v = VideoConfig(
        video_id="EXAMPLE_VID01",
        video_url="https://www.youtube.com/live/EXAMPLE_VID01",
        tier="Tier 2", division="Preteen", gender="Female", stage="Stage 1",
        timestamp_buffer_seconds=5,
    )
    c = Candidate(
        detected_start_seconds=1126.0,
        pattern_name="our_next_competitor_is",
        pattern_weight=1.0,
        athlete_name_raw="Jane Example",
        athlete_name_clean="Jane Example",
    )
    run = _candidate_to_run(c, v, order=1)
    assert run["run_id"] == "EXAMPLE_VID01_001"
    assert run["timestamp_seconds"] == 1121
    assert run["timestamp_hhmmss"] == "00:18:41"
    assert run["youtube_run_url"] == "https://youtu.be/EXAMPLE_VID01?t=1121"
    assert run["review_status"] == "unreviewed"
    assert run["start_source"] == "transcript"
