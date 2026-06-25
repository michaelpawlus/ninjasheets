"""Detect candidate athlete announcements in a normalized transcript.

Strategy (Phase 1, transcript-only):

1. Concatenate normalized transcript lines into one flowing string while keeping
   a char-offset -> timestamp map (announcements often straddle line breaks).
2. Run the announcement regexes over the flowing text.
3. For each hit, clean the candidate name, then look in a +/- context window for
   gym and location cues.
4. Deduplicate repeated mentions of the same athlete within a time window,
   keeping the earliest plausible timestamp.
5. Score confidence from the matched pattern and corroborating cues.

We never invent names. Every candidate carries the transcript text that
triggered it and is exported as ``unreviewed``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import ExtractionPatterns
from .transcript import TranscriptLine

# Words that look like names but are commentary; if the WHOLE candidate is one
# of these (or a leading filler), reject or trim it.
_TITLECASE = re.compile(r"^[A-Z][A-Za-z'.\-]*$")


@dataclass
class Candidate:
    detected_start_seconds: float
    pattern_name: str
    pattern_weight: float
    athlete_name_raw: str
    athlete_name_clean: str
    gym_raw: str = ""
    city: str = ""
    state: str = ""
    detected_text: str = ""
    context_text: str = ""
    confidence: str = "low"
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)


class _FlowText:
    """Flowing transcript text with offset -> timestamp lookup."""

    def __init__(self, lines: list[TranscriptLine]):
        self.text = ""
        self._offsets: list[int] = []  # char offset where each line begins
        self._starts: list[float] = []
        parts = []
        cursor = 0
        for ln in lines:
            self._offsets.append(cursor)
            self._starts.append(ln.start_seconds)
            parts.append(ln.text_normalized)
            cursor += len(ln.text_normalized) + 1  # +1 for the joining space
        self.text = " ".join(parts)

    def time_at(self, char_offset: int) -> float:
        """Timestamp of the line containing ``char_offset`` (binary search)."""
        import bisect

        i = bisect.bisect_right(self._offsets, char_offset) - 1
        return self._starts[max(0, i)]

    def window(self, t0: float, t1: float, lines: list[TranscriptLine]) -> str:
        return " ".join(
            ln.text_normalized for ln in lines if t0 <= ln.start_seconds <= t1
        )


def clean_name(raw: str, patterns: ExtractionPatterns) -> str:
    """Trim filler/punctuation without over-cleaning. Raw is kept separately."""
    tokens = raw.strip().strip(".,").split()
    while tokens and tokens[0].lower() in patterns.name_leading_filler:
        tokens.pop(0)
    # Title-case only fully-upper or fully-lower tokens; leave McX/O'X alone.
    out = []
    for tok in tokens:
        if tok.isupper() or tok.islower():
            out.append(tok.capitalize())
        else:
            out.append(tok)
    return " ".join(out)


def _is_valid_name(name: str, patterns: ExtractionPatterns) -> bool:
    tokens = name.split()
    if not tokens:
        return False
    if len(tokens) == 1 and tokens[0] in patterns.name_stopwords:
        return False
    if all(t in patterns.name_stopwords for t in tokens):
        return False
    return all(_TITLECASE.match(t) for t in tokens)


def _find_gym(context: str, patterns: ExtractionPatterns) -> str:
    for pat in patterns.gym:
        m = pat.search(context)
        if m:
            return m.group("gym").strip(" .,").rstrip()
    return ""


def _find_location(context: str, patterns: ExtractionPatterns) -> tuple[str, str]:
    for pat in patterns.location:
        m = pat.search(context)
        if m:
            return m.group("city").strip(" .,"), m.group("state").strip(" .,")
    return "", ""


def _score(c: Candidate, patterns: ExtractionPatterns) -> None:
    """Populate score / confidence / reasons from corroborating signals."""
    score = c.pattern_weight
    c.reasons.append(f"pattern:{c.pattern_name}({c.pattern_weight:g})")
    if c.gym_raw:
        score += 0.15
        c.reasons.append("gym_cue")
    if c.city and c.state:
        score += 0.15
        c.reasons.append("location_cue")
    if len(c.athlete_name_clean.split()) >= 2:
        score += 0.1
        c.reasons.append("multi_token_name")
    else:
        c.reasons.append("single_token_name")
    c.score = round(score, 3)
    if score >= 1.1:
        c.confidence = "high"
    elif score >= 0.8:
        c.confidence = "medium"
    else:
        c.confidence = "low"


def extract_candidates(
    lines: list[TranscriptLine],
    patterns: ExtractionPatterns,
    dedup_window_seconds: float = 60.0,
    context_before: float = 10.0,
    context_after: float = 20.0,
) -> list[Candidate]:
    flow = _FlowText(lines)
    raw_hits: list[Candidate] = []

    for pat in patterns.announcement:
        for m in pat.regex.finditer(flow.text):
            name_raw = m.group("name")
            name_clean = clean_name(name_raw, patterns)
            if not _is_valid_name(name_clean, patterns):
                continue
            t = flow.time_at(m.start())
            ctx = flow.window(t - context_before, t + context_after, lines)
            gym = _find_gym(ctx, patterns)
            city, state = _find_location(ctx, patterns)
            cand = Candidate(
                detected_start_seconds=t,
                pattern_name=pat.name,
                pattern_weight=pat.weight,
                athlete_name_raw=name_raw,
                athlete_name_clean=name_clean,
                gym_raw=gym,
                city=city,
                state=state,
                detected_text=m.group(0),
                context_text=ctx,
            )
            _score(cand, patterns)
            raw_hits.append(cand)

    return _deduplicate(raw_hits, dedup_window_seconds)


def _deduplicate(
    hits: list[Candidate], window_seconds: float
) -> list[Candidate]:
    """Collapse same-name mentions within ``window_seconds``; keep earliest.

    Also drop a lower-confidence hit that lands within the window of an already
    accepted, different-name hit only if names match; different athletes close
    in time are legitimately distinct runs and are kept.
    """
    hits.sort(key=lambda c: c.detected_start_seconds)
    kept: list[Candidate] = []
    last_by_name: dict[str, Candidate] = {}
    for c in hits:
        key = c.athlete_name_clean.lower()
        prev = last_by_name.get(key)
        if prev and (c.detected_start_seconds - prev.detected_start_seconds) <= window_seconds:
            # Same athlete restated; enrich the earlier row if this one has more.
            if not prev.gym_raw and c.gym_raw:
                prev.gym_raw = c.gym_raw
            if not (prev.city and prev.state) and c.city and c.state:
                prev.city, prev.state = c.city, c.state
            continue
        kept.append(c)
        last_by_name[key] = c
    kept.sort(key=lambda c: c.detected_start_seconds)
    return kept
