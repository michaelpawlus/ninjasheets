"""Load video configs and extraction patterns from ``config/``."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .utils import project_root


@dataclass
class VideoConfig:
    video_id: str
    video_url: str
    video_title: str = ""
    event_name: str = ""
    season: str = ""
    competition_name: str = ""
    tier: str = ""
    division: str = ""
    gender: str = ""
    stage: str = ""
    course: str = ""
    date: str = ""
    timestamp_buffer_seconds: int = 5
    expected_extraction_methods: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "VideoConfig":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass
class CompiledPattern:
    name: str
    regex: re.Pattern[str]
    weight: float


@dataclass
class ExtractionPatterns:
    announcement: list[CompiledPattern]
    gym: list[re.Pattern[str]]
    location: list[re.Pattern[str]]
    name_stopwords: set[str]
    name_leading_filler: list[str]


def config_dir() -> Path:
    return project_root() / "config"


def load_videos(path: Path | None = None) -> list[VideoConfig]:
    path = path or (config_dir() / "videos.yaml")
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. The real video config is local-only (git-ignored). "
            "Create it from the template:\n"
            "    cp config/videos.example.yaml config/videos.yaml\n"
            "then edit it with the video you want to process."
        )
    data = yaml.safe_load(path.read_text()) or {}
    return [VideoConfig.from_dict(v) for v in data.get("videos", [])]


def get_video(video_id: str, path: Path | None = None) -> VideoConfig:
    for v in load_videos(path):
        if v.video_id == video_id:
            return v
    raise KeyError(f"video_id {video_id!r} not found in videos.yaml")


def load_patterns(path: Path | None = None) -> ExtractionPatterns:
    path = path or (config_dir() / "extraction_patterns.yaml")
    data = yaml.safe_load(path.read_text()) or {}
    # Patterns use scoped (?i:...) flags on their trigger words only, so names
    # and proper nouns stay case-sensitive (Title Case). Do NOT apply a global
    # IGNORECASE here -- it would defeat that and re-introduce over-capture.
    announcement = [
        CompiledPattern(p["name"], re.compile(p["regex"]), float(p.get("weight", 1.0)))
        for p in data.get("announcement_patterns", [])
    ]
    gym = [re.compile(p) for p in data.get("gym_patterns", [])]
    location = [re.compile(p) for p in data.get("location_patterns", [])]
    return ExtractionPatterns(
        announcement=announcement,
        gym=gym,
        location=location,
        name_stopwords=set(data.get("name_stopwords", [])),
        name_leading_filler=[w.lower() for w in data.get("name_leading_filler", [])],
    )
