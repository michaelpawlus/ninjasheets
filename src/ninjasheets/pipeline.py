"""Orchestrate the Phase 1 one-video pipeline into in-memory tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import youtube
from .config import VideoConfig, load_patterns
from .enrichment import enrich_result
from .parsing import Candidate, extract_candidates
from .transcript import TranscriptLine, load_json3
from .utils import apply_timestamp_buffer, hhmmss, youtube_run_url

# Canonical Runs column order (technical fields last) -- mirrors the spec.
RUN_COLUMNS = [
    "run_id",
    "event_name",
    "season",
    "competition_name",
    "video_id",
    "video_url",
    "video_title",
    "tier",
    "division",
    "gender",
    "stage",
    "course",
    "date",
    "wave",
    "run_order_in_wave",
    "run_order_overall",
    "athlete_name_raw",
    "athlete_name_clean",
    "gym_raw",
    "gym_normalized",
    "city",
    "state",
    "country",
    "athlete_id",
    "matched_athlete_name",
    "athlete_match_status",
    "athlete_match_score",
    "enrichment_source",
    "enrichment_review_status",
    "detected_announcement_time_seconds",
    "timestamp_seconds",
    "timestamp_hhmmss",
    "youtube_run_url",
    "detected_text",
    "start_source",
    "source_confidence",
    "review_status",
    "notes",
]


@dataclass
class PipelineResult:
    video: VideoConfig
    metadata: dict
    transcript_lines: list[TranscriptLine]
    candidates: list[Candidate]
    runs: list[dict]
    log: list[dict] = field(default_factory=list)
    athletes: list[dict] = field(default_factory=list)
    gyms: list[dict] = field(default_factory=list)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _candidate_to_run(c: Candidate, video: VideoConfig, order: int) -> dict:
    detected = c.detected_start_seconds
    ts = apply_timestamp_buffer(detected, video.timestamp_buffer_seconds)
    return {
        "run_id": f"{video.video_id}_{order:03d}",
        "event_name": video.event_name,
        "season": video.season,
        "competition_name": video.competition_name,
        "video_id": video.video_id,
        "video_url": video.video_url,
        "video_title": video.video_title,
        "tier": video.tier,
        "division": video.division,
        "gender": video.gender,
        "stage": video.stage,
        "course": video.course,
        "date": video.date,
        "wave": "",
        "run_order_in_wave": "",
        "run_order_overall": order,
        "athlete_name_raw": c.athlete_name_raw,
        "athlete_name_clean": c.athlete_name_clean,
        "gym_raw": c.gym_raw,
        "gym_normalized": "",
        "city": c.city,
        "state": c.state,
        "country": "",
        "athlete_id": "",
        "matched_athlete_name": "",
        "athlete_match_status": "",
        "athlete_match_score": "",
        "enrichment_source": "",
        "enrichment_review_status": "",
        "detected_announcement_time_seconds": int(round(detected)),
        "timestamp_seconds": ts,
        "timestamp_hhmmss": hhmmss(ts),
        "youtube_run_url": youtube_run_url(video.video_id, ts),
        "detected_text": c.detected_text,
        "start_source": "transcript",
        "source_confidence": c.confidence,
        "review_status": "unreviewed",
        "notes": "; ".join(c.reasons),
    }


def run_pipeline(
    video: VideoConfig, force: bool = False, index_db: Path | None = None
) -> PipelineResult:
    log: list[dict] = []

    def step(name: str, status: str, **extra):
        log.append({"run_datetime": _now(), "video_id": video.video_id,
                    "step": name, "status": status, **extra})

    meta = youtube.fetch_metadata(video.video_id, force=force)
    step("fetch_metadata", "ok", notes=f"duration={meta.get('duration')}s")

    transcript_path: Path | None = youtube.fetch_transcript(video.video_id, force=force)
    if not transcript_path:
        step("fetch_transcript", "failed", warnings="no captions available")
        return PipelineResult(video, meta, [], [], [], log)
    step("fetch_transcript", "ok", notes=transcript_path.name)

    lines = load_json3(transcript_path, video.video_id)
    step("normalize_transcript", "ok", rows_created=len(lines))

    patterns = load_patterns()
    candidates = extract_candidates(lines, patterns)
    step("extract_candidates", "ok", rows_created=len(candidates))

    runs = [_candidate_to_run(c, video, i + 1) for i, c in enumerate(candidates)]
    needs_review = sum(1 for r in runs if r["source_confidence"] == "low")
    step("build_runs", "ok", rows_created=len(runs),
         warnings=f"{needs_review} low-confidence rows")

    athletes, gyms = enrich_result(runs, index_db=index_db)
    matched = sum(1 for r in runs
                  if r["athlete_match_status"] in ("verified", "high_confidence"))
    step("enrich_runs", "ok", rows_created=len(athletes),
         notes=f"{matched}/{len(runs)} athletes auto-filled; {len(gyms)} gyms")

    return PipelineResult(video, meta, lines, candidates, runs, log, athletes, gyms)
