"""Normalize a yt-dlp json3 transcript into timestamped lines."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptLine:
    video_id: str
    start_seconds: float
    duration_seconds: float
    text_raw: str
    text_normalized: str

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


_WS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse whitespace and drop caption noise tokens like ``[music]``/``>>``."""
    t = re.sub(r"\[[^\]]*\]", " ", text)  # [music], [crying], ...
    t = t.replace(">>", " ")
    t = _WS.sub(" ", t).strip()
    return t


def load_json3(path: Path, video_id: str) -> list[TranscriptLine]:
    data = json.loads(Path(path).read_text())
    lines: list[TranscriptLine] = []
    for event in data.get("events", []):
        segs = event.get("segs")
        if not segs:
            continue
        raw = "".join(s.get("utf8", "") for s in segs).strip()
        if not raw:
            continue
        start = event.get("tStartMs", 0) / 1000.0
        dur = event.get("dDurationMs", 0) / 1000.0
        norm = normalize_text(raw)
        if not norm:
            continue
        lines.append(TranscriptLine(video_id, start, dur, raw, norm))
    return lines
