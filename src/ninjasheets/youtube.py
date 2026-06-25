"""Retrieve video metadata and transcripts via ``yt-dlp``.

We shell out to yt-dlp (already a dependency) rather than import it, so the same
commands are easy to reproduce by hand for debugging. All raw outputs are kept
under ``data/raw/`` per the spec -- never rely only on parsed strings.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .utils import project_root


def _raw_dir(*parts: str) -> Path:
    d = project_root() / "data" / "raw" / Path(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def watch_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_metadata(video_id: str, force: bool = False) -> dict:
    """Download full yt-dlp metadata JSON and cache it under data/raw."""
    out = _raw_dir("video_metadata") / f"{video_id}.json"
    if out.exists() and not force:
        return json.loads(out.read_text())
    proc = subprocess.run(
        ["yt-dlp", "--skip-download", "--dump-json", watch_url(video_id)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp metadata failed: {proc.stderr[-500:]}")
    out.write_text(proc.stdout)
    return json.loads(proc.stdout)


def fetch_transcript(
    video_id: str, lang: str = "en-orig", force: bool = False
) -> Path | None:
    """Download auto-captions as json3. Returns the file path, or None if absent.

    Tries the requested language first, then falls back to plain ``en``.
    """
    out_dir = _raw_dir("transcripts")
    for candidate in (lang, "en", "en-US"):
        existing = out_dir / f"{video_id}.{candidate}.json3"
        if existing.exists() and not force:
            return existing
    template = str(out_dir / "%(id)s.%(ext)s")
    proc = subprocess.run(
        [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs",
            f"{lang},en,en-US",
            "--sub-format",
            "json3",
            "-o",
            template,
            watch_url(video_id),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp transcript failed: {proc.stderr[-500:]}")
    for candidate in (lang, "en", "en-US"):
        path = out_dir / f"{video_id}.{candidate}.json3"
        if path.exists():
            return path
    return None
