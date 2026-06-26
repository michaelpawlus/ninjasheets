"""Phase 2 athlete/gym enrichment.

Joins each run row to a reference athlete roster (the WNL-Athlete-Video-Index
SQLite DB, a local sibling project) with ``rapidfuzz``, normalizes gyms via
``config/gym_aliases.csv``, and applies manual corrections from
``config/athlete_overrides.csv``. Overrides take precedence and persist across
runs (spec §12.3).

Design principle (spec §12): **do not silently overmatch.** Every run gets an
explicit ``athlete_match_status``:

    verified | high_confidence | medium_confidence | low_confidence
            | ambiguous | not_found

One high-confidence match -> auto-fill. Two or more plausible, distinct people
within a small score band -> ``ambiguous`` (we fill nothing). No good match ->
``not_found``. A human correction (override) -> ``verified``.

Data boundary: the reference roster contains real names (minors) and the
override file maps real names to gyms. Both are read from local, git-ignored
sources at runtime. Nothing real is committed; this module only contains logic.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz

from .utils import project_root

# --- score thresholds (0-100) -------------------------------------------------
HIGH_SCORE = 92
MEDIUM_SCORE = 82
LOW_SCORE = 72
# Two distinct people whose top scores fall within this band -> ambiguous.
AMBIGUITY_DELTA = 6
# A bare first name is weak evidence: widen the band so same-first-name twins
# (e.g. "Sloane" vs "Sloan") resolve to ambiguous rather than auto-picking one.
SINGLE_TOKEN_DELTA = 12

# Division labels we recognize when parsing a free-form "Preteen Female" string.
_DIVISION_WORDS = [
    "Preteen", "Teen", "Junior", "Mature", "Adult", "Open", "Kid", "Youth",
]

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


# --- data shapes --------------------------------------------------------------
@dataclass
class RefAthlete:
    full_name: str
    first_name: str
    athlete_id: str = ""
    division: str = ""
    gender: str = ""
    region: str = ""
    season: str = ""
    source_url: str = ""
    source_type: str = ""
    gym_raw: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    full_norm: str = ""
    first_norm: str = ""


@dataclass
class GymInfo:
    gym_normalized: str = ""
    city: str = ""
    state: str = ""
    country: str = ""


@dataclass
class MatchResult:
    status: str = "not_found"
    score: int = 0
    athlete_id: str = ""
    matched_athlete_name: str = ""
    source: str = ""
    gym_raw: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    candidates: list[str] = field(default_factory=list)


# --- normalization ------------------------------------------------------------
def normalize_name(value: str) -> str:
    """Accent-fold, lowercase, and collapse to a stable matching key.

    "Esmé Newton-Pawlus" -> "esme newton pawlus". Empty in -> empty out.
    """
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    lowered = stripped.lower()
    return _NON_ALNUM.sub(" ", lowered).strip()


def _split_division_gender(label: str) -> tuple[str, str]:
    """Pull a (division, gender) pair out of a free-form label like
    "Preteen Female" or "WNL Preteen Female / US-Midwest / Season XI"."""
    low = label.lower()
    gender = ""
    if "female" in low:
        gender = "Female"
    elif "male" in low:  # 'female' already handled above
        gender = "Male"
    division = ""
    for word in _DIVISION_WORDS:
        if word.lower() in low:
            division = word
            break
    return division, gender


# --- reference roster loading -------------------------------------------------
def default_index_db_path() -> Path:
    """Default location of the sibling WNL-Athlete-Video-Index database.

    Overridable via the ``NINJASHEETS_ATHLETE_INDEX_DB`` env var or a CLI flag.
    The path points at a *local* sibling repo; the data it holds stays local.
    """
    env = os.environ.get("NINJASHEETS_ATHLETE_INDEX_DB")
    if env:
        return Path(env).expanduser()
    return (
        project_root().parent
        / "WNL-Athlete-Video-Index"
        / "data"
        / "wnl_athlete_video_index.db"
    )


def _ref_from_names(
    full_name: str,
    first_name: str,
    division: str,
    gender: str,
    *,
    athlete_id: str = "",
    region: str = "",
    season: str = "",
    source_url: str = "",
    source_type: str = "",
    gym_raw: str = "",
    city: str = "",
    state: str = "",
    country: str = "",
) -> RefAthlete | None:
    full_name = (full_name or "").strip()
    if not full_name:
        return None
    first_name = (first_name or full_name.split()[0]).strip()
    return RefAthlete(
        full_name=full_name,
        first_name=first_name,
        athlete_id=str(athlete_id or ""),
        division=division,
        gender=gender,
        region=region,
        season=season,
        source_url=source_url,
        source_type=source_type,
        gym_raw=(gym_raw or "").strip(),
        city=(city or "").strip(),
        state=(state or "").strip(),
        country=(country or "").strip(),
        full_norm=normalize_name(full_name),
        first_norm=normalize_name(first_name),
    )


def load_reference_roster(
    db_path: Path | None = None,
    known_json_path: Path | None = None,
) -> list[RefAthlete]:
    """Build the reference roster from the index DB + known_athletes.json.

    Both sources are optional; a missing source is skipped (enrichment then
    degrades to overrides + gym normalization only). Entries are de-duplicated
    by normalized full name, preferring a row that carries an ``athlete_id``.
    """
    db_path = db_path or default_index_db_path()
    if known_json_path is None and db_path:
        known_json_path = db_path.parent / "known_athletes.json"

    refs: list[RefAthlete] = []

    if db_path and Path(db_path).exists():
        refs.extend(_load_roster_from_db(Path(db_path)))

    if known_json_path and Path(known_json_path).exists():
        refs.extend(_load_roster_from_known_json(Path(known_json_path)))

    # De-dup by normalized full name; keep the entry with the richest id/source.
    by_key: dict[str, RefAthlete] = {}
    for ref in refs:
        existing = by_key.get(ref.full_norm)
        if existing is None:
            by_key[ref.full_norm] = ref
            continue
        if not existing.athlete_id and ref.athlete_id:
            existing.athlete_id = ref.athlete_id
        if not existing.source_url and ref.source_url:
            existing.source_url = ref.source_url
            existing.source_type = ref.source_type
    return list(by_key.values())


# Optional columns the roster will pick up *if* the index ever gains them
# (e.g. seeded from NinjaWorks/WNL results that list a club). Today they don't
# exist, so this is a no-op -- but the moment a gym/city/state column is added
# to competition_athletes, matched athletes inherit that gym automatically.
_OPTIONAL_REF_COLS = {
    "gym_raw": ("gym_raw", "gym", "gym_name", "club", "team"),
    "city": ("city",),
    "state": ("state", "province"),
    "country": ("country",),
}


def _load_roster_from_db(db_path: Path) -> list[RefAthlete]:
    rows: list[RefAthlete] = []
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        con.row_factory = sqlite3.Row
        have = {
            r["name"]
            for r in con.execute("PRAGMA table_info(competition_athletes)").fetchall()
        }
        # Resolve each optional field to the first matching real column, if any.
        selected: dict[str, str] = {}
        for field_name, candidates in _OPTIONAL_REF_COLS.items():
            for col in candidates:
                if col in have:
                    selected[field_name] = col
                    break
        extra_sql = "".join(f", ca.{col} AS {field}" for field, col in selected.items())
        cur = con.execute(
            f"""
            SELECT ca.athlete_full_name AS full_name,
                   ca.athlete_first_name AS first_name,
                   c.division AS division,
                   c.region   AS region,
                   c.season   AS season{extra_sql}
            FROM competition_athletes ca
            JOIN competitions c ON ca.competition_id = c.id
            """
        )
        for r in cur.fetchall():
            keys = r.keys()
            division, gender = _split_division_gender(r["division"] or "")
            ref = _ref_from_names(
                r["full_name"],
                r["first_name"],
                division,
                gender,
                region=r["region"] or "",
                season=r["season"] or "",
                source_type="official_index",
                gym_raw=r["gym_raw"] if "gym_raw" in keys else "",
                city=r["city"] if "city" in keys else "",
                state=r["state"] if "state" in keys else "",
                country=r["country"] if "country" in keys else "",
            )
            if ref:
                rows.append(ref)
    finally:
        con.close()
    return rows


def _load_roster_from_known_json(path: Path) -> list[RefAthlete]:
    data = json.loads(path.read_text())
    meta = data.get("meta", {})
    division, gender = _split_division_gender(meta.get("source", ""))
    source_url = meta.get("ninjaworks_url", "")
    rows: list[RefAthlete] = []
    for a in data.get("athletes", []):
        ref = _ref_from_names(
            a.get("full_name", ""),
            a.get("first_name", ""),
            division,
            gender,
            athlete_id=a.get("db_athlete_id") or "",
            source_url=source_url,
            source_type="official_index",
        )
        if ref:
            rows.append(ref)
    return rows


# --- config tables ------------------------------------------------------------
def config_path(name: str) -> Path:
    return project_root() / "config" / name


def load_gym_aliases(path: Path | None = None) -> dict[str, GymInfo]:
    """Map a normalized raw gym string -> canonical GymInfo.

    Falls back to the committed ``.example`` template when no local file exists,
    so a fresh checkout still normalizes the demo gyms.
    """
    if path is None:
        path = config_path("gym_aliases.csv")
        if not path.exists():
            path = config_path("gym_aliases.example.csv")
    if not path.exists():
        return {}
    out: dict[str, GymInfo] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            raw = (row.get("gym_raw") or "").strip()
            if not raw:
                continue
            out[normalize_name(raw)] = GymInfo(
                gym_normalized=(row.get("gym_normalized") or raw).strip(),
                city=(row.get("city") or "").strip(),
                state=(row.get("state") or "").strip(),
                country=(row.get("country") or "").strip(),
            )
    return out


def load_overrides(path: Path | None = None) -> dict[str, dict]:
    """Manual athlete corrections keyed by normalized ``athlete_name_clean``.

    The real file (``athlete_overrides.csv``) is git-ignored; only the synthetic
    ``.example`` is committed. A missing file simply means no overrides.
    """
    if path is None:
        path = config_path("athlete_overrides.csv")
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("athlete_name_clean") or "").strip()
            if not name:
                continue
            out[normalize_name(name)] = {k: (v or "").strip() for k, v in row.items()}
    return out


def normalize_gym(gym_raw: str, aliases: dict[str, GymInfo]) -> GymInfo:
    """Resolve a raw transcript gym cue to a canonical gym. Unknown gyms keep
    their cleaned raw text as the normalized name (we don't invent details)."""
    raw = (gym_raw or "").strip()
    if not raw:
        return GymInfo()
    hit = aliases.get(normalize_name(raw))
    if hit:
        return GymInfo(hit.gym_normalized, hit.city, hit.state, hit.country)
    return GymInfo(gym_normalized=raw)


# --- matching -----------------------------------------------------------------
def _same_division_gender(ref: RefAthlete, division: str, gender: str) -> bool:
    if gender and ref.gender and gender.lower() != ref.gender.lower():
        return False
    if division and ref.division and division.lower() != ref.division.lower():
        return False
    return True


def _score_ref(name_norm: str, single_token: bool, ref: RefAthlete) -> int:
    score = fuzz.WRatio(name_norm, ref.full_norm)
    if single_token:
        # A bare first name ("Esme") should still light up "Esmé Newton-Pawlus".
        score = max(score, fuzz.ratio(name_norm, ref.first_norm))
    return int(round(score))


def match_athlete(
    name_clean: str,
    division: str,
    gender: str,
    roster: list[RefAthlete],
    overrides: dict[str, dict] | None = None,
) -> MatchResult:
    """Resolve one run's athlete name against the roster.

    Order: manual override (->verified) first, then rapidfuzz against the
    division/gender-filtered roster with explicit confidence banding.
    """
    name_norm = normalize_name(name_clean)
    if not name_norm:
        return MatchResult(status="not_found")

    overrides = overrides or {}
    ov = overrides.get(name_norm)
    if ov:
        return MatchResult(
            status="verified",
            score=100,
            athlete_id=ov.get("athlete_id", ""),
            matched_athlete_name=ov.get("matched_athlete_name")
            or ov.get("athlete_name_clean")
            or name_clean,
            source="override",
        )

    candidates = [r for r in roster if _same_division_gender(r, division, gender)]
    if not candidates:
        return MatchResult(status="not_found")

    single_token = len(name_norm.split()) == 1
    scored = sorted(
        ((_score_ref(name_norm, single_token, r), r) for r in candidates),
        key=lambda t: t[0],
        reverse=True,
    )
    top_score, top_ref = scored[0]

    if top_score < LOW_SCORE:
        return MatchResult(status="not_found", score=top_score)

    # Distinct people clustered near the top => genuinely ambiguous.
    delta = SINGLE_TOKEN_DELTA if single_token else AMBIGUITY_DELTA
    near = [
        r
        for sc, r in scored
        if top_score - sc <= delta and r.full_norm != top_ref.full_norm
    ]
    if near:
        names = [top_ref.full_name] + [r.full_name for r in near]
        return MatchResult(
            status="ambiguous",
            score=top_score,
            source=top_ref.source_type,
            candidates=names,
        )

    if top_score >= HIGH_SCORE:
        status = "high_confidence"
    elif top_score >= MEDIUM_SCORE:
        status = "medium_confidence"
    else:
        status = "low_confidence"

    return MatchResult(
        status=status,
        score=top_score,
        athlete_id=top_ref.athlete_id,
        matched_athlete_name=top_ref.full_name,
        source=top_ref.source_type or "official_index",
        gym_raw=top_ref.gym_raw,
        city=top_ref.city,
        state=top_ref.state,
        country=top_ref.country,
    )


# --- enrichment orchestration -------------------------------------------------
# Statuses at/above this bar auto-fill athlete_id / matched_athlete_name.
_AUTOFILL = {"verified", "high_confidence"}


def _slug(value: str) -> str:
    return normalize_name(value).replace(" ", "-")


def enrich_runs(
    runs: list[dict],
    roster: list[RefAthlete],
    overrides: dict[str, dict],
    gym_aliases: dict[str, GymInfo],
) -> tuple[list[dict], list[dict]]:
    """Mutate ``runs`` in place with enrichment columns and return
    ``(athletes_rows, gyms_rows)`` for the workbook's enrichment tabs."""
    athletes: dict[str, dict] = {}
    gyms: dict[str, dict] = {}

    for run in runs:
        division = run.get("division", "")
        gender = run.get("gender", "")
        name_clean = run.get("athlete_name_clean", "")

        match = match_athlete(name_clean, division, gender, roster, overrides)
        ov = overrides.get(normalize_name(name_clean), {})

        # Gym precedence: transcript cue -> matched-athlete's index gym -> override.
        gym_source_raw = run.get("gym_raw", "") or (
            match.gym_raw if match.status in _AUTOFILL else ""
        )
        gym = normalize_gym(gym_source_raw, gym_aliases)
        if not run.get("gym_raw", "") and match.status in _AUTOFILL:
            # Index supplied the gym; carry its location too when present.
            gym.city = gym.city or match.city
            gym.state = gym.state or match.state
            gym.country = gym.country or match.country
        if ov.get("gym_normalized"):
            gym = GymInfo(
                gym_normalized=ov["gym_normalized"],
                city=ov.get("city", "") or gym.city,
                state=ov.get("state", "") or gym.state,
                country=ov.get("country", "") or gym.country,
            )

        autofill = match.status in _AUTOFILL
        run["athlete_id"] = match.athlete_id if autofill else ""
        run["athlete_match_status"] = match.status
        run["athlete_match_score"] = match.score
        run["matched_athlete_name"] = match.matched_athlete_name if autofill else ""
        run["gym_normalized"] = gym.gym_normalized
        # Prefer existing transcript city/state; fall back to gym/override.
        run["city"] = run.get("city", "") or gym.city
        run["state"] = run.get("state", "") or gym.state
        run["country"] = run.get("country", "") or gym.country

        sources = []
        if match.status == "verified":
            sources.append("override")
        elif autofill and match.source:
            sources.append(match.source)
        if run["gym_normalized"]:
            if ov.get("gym_normalized"):
                sources.append("override")
            elif run.get("gym_raw", ""):
                sources.append("transcript_gym")
            else:
                sources.append("index_gym")
        run["enrichment_source"] = "; ".join(dict.fromkeys(sources))
        run["enrichment_review_status"] = (
            "verified" if match.status == "verified" else "unreviewed"
        )
        if match.status == "ambiguous" and match.candidates:
            note = "ambiguous: " + " | ".join(match.candidates)
            run["notes"] = f"{run.get('notes', '')}; {note}".strip("; ")

        _accumulate_athlete(athletes, run, match, autofill)
        _accumulate_gym(gyms, run, gym)

    return list(athletes.values()), list(gyms.values())


def _accumulate_athlete(
    athletes: dict[str, dict], run: dict, match: MatchResult, autofill: bool
) -> None:
    display = run["matched_athlete_name"] if autofill else run.get("athlete_name_clean", "")
    if not display:
        return
    key = normalize_name(display)
    row = athletes.get(key)
    if row is None:
        athletes[key] = {
            "athlete_id": run.get("athlete_id", ""),
            "athlete_name": display,
            "athlete_name_normalized": key,
            "gym_raw": run.get("gym_raw", ""),
            "gym_normalized": run.get("gym_normalized", ""),
            "city": run.get("city", ""),
            "state": run.get("state", ""),
            "country": run.get("country", ""),
            "source_url": "",
            "source_type": match.source or "transcript",
            "last_updated": run.get("date", ""),
        }
        return
    # Backfill anything the first occurrence lacked.
    for col in ("athlete_id", "gym_raw", "gym_normalized", "city", "state", "country"):
        if not row.get(col) and run.get(col):
            row[col] = run[col]


def _accumulate_gym(gyms: dict[str, dict], run: dict, gym: GymInfo) -> None:
    if not gym.gym_normalized:
        return
    key = normalize_name(gym.gym_normalized)
    row = gyms.get(key)
    raw = run.get("gym_raw", "")
    if row is None:
        gyms[key] = {
            "gym_id": _slug(gym.gym_normalized),
            "gym_raw": raw,
            "gym_normalized": gym.gym_normalized,
            "city": gym.city or run.get("city", ""),
            "state": gym.state or run.get("state", ""),
            "country": gym.country or run.get("country", ""),
            "source_url": "",
            "notes": "",
            "_raw_variants": {raw} if raw else set(),
        }
        return
    for col in ("city", "state", "country"):
        if not row.get(col) and (getattr(gym, col) or run.get(col)):
            row[col] = getattr(gym, col) or run.get(col)
    if raw:
        row["_raw_variants"].add(raw)


def enrich_result(runs: list[dict], index_db: Path | None = None) -> tuple[list[dict], list[dict]]:
    """Top-level convenience: load every reference source from disk and enrich.

    Returns ``(athletes_rows, gyms_rows)``; ``runs`` is mutated in place. The
    ``_raw_variants`` helper key is folded into the gym ``notes`` column here.
    """
    roster = load_reference_roster(index_db)
    overrides = load_overrides()
    gym_aliases = load_gym_aliases()
    athletes, gyms = enrich_runs(runs, roster, overrides, gym_aliases)
    for g in gyms:
        variants = g.pop("_raw_variants", set())
        extra = sorted(v for v in variants if v and v != g["gym_normalized"])
        if extra:
            g["notes"] = "aka: " + "; ".join(extra)
    return athletes, gyms
