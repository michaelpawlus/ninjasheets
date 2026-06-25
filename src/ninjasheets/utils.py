"""Small shared helpers: timestamps, links, paths."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Repo root, resolved relative to this file (src/ninjasheets/utils.py)."""
    return Path(__file__).resolve().parents[2]


def hhmmss(seconds: float | int) -> str:
    """Format whole seconds as H:MM:SS (or HH:MM:SS), matching YouTube display."""
    s = max(0, int(round(seconds)))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{sec:02d}"
    return f"00:{m:02d}:{sec:02d}"


def youtube_run_url(video_id: str, timestamp_seconds: int) -> str:
    """Direct, share-friendly run link that jumps to ``timestamp_seconds``."""
    return f"https://youtu.be/{video_id}?t={int(timestamp_seconds)}"


def apply_timestamp_buffer(detected_seconds: float, buffer_seconds: int) -> int:
    """Back the link up a few seconds so the viewer gets run-start context."""
    return max(0, int(round(detected_seconds)) - int(buffer_seconds))
