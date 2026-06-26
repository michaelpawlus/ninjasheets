"""Phase 2 enrichment tests. Synthetic athletes only (data boundary)."""

from __future__ import annotations

from ninjasheets.enrichment import (
    GymInfo,
    RefAthlete,
    dedupe_roster,
    enrich_runs,
    load_overrides,
    match_athlete,
    normalize_gym,
    normalize_name,
)


def _ref(full: str, first: str, athlete_id: str = "") -> RefAthlete:
    return RefAthlete(
        full_name=full,
        first_name=first,
        athlete_id=athlete_id,
        division="Preteen",
        gender="Female",
        source_type="official_index",
        full_norm=normalize_name(full),
        first_norm=normalize_name(first),
    )


ROSTER = [
    _ref("Jane Example", "Jane", "1001"),
    _ref("Alex Sample", "Alex"),
    _ref("Quinn Tester", "Quinn"),
    _ref("Quinn Probe", "Quinn"),  # same first name -> collisions are ambiguous
]


def test_normalize_name_folds_accents_and_punct():
    assert normalize_name("Esmé Newton-Pawlus") == "esme newton pawlus"
    assert normalize_name("  O'Brien ") == "o brien"
    assert normalize_name("") == ""


def test_full_name_exact_match_is_high_confidence():
    m = match_athlete("Jane Example", "Preteen", "Female", ROSTER)
    assert m.status == "high_confidence"
    assert m.matched_athlete_name == "Jane Example"
    assert m.athlete_id == "1001"


def test_single_first_name_collision_is_ambiguous():
    m = match_athlete("Quinn", "Preteen", "Female", ROSTER)
    assert m.status == "ambiguous"
    assert set(m.candidates) == {"Quinn Tester", "Quinn Probe"}
    assert m.matched_athlete_name == ""  # nothing auto-filled


def test_unique_first_name_resolves():
    m = match_athlete("Jane", "Preteen", "Female", ROSTER)
    assert m.status == "high_confidence"
    assert m.matched_athlete_name == "Jane Example"


def test_no_match_is_not_found():
    m = match_athlete("Zzyzx Nobody", "Preteen", "Female", ROSTER)
    assert m.status == "not_found"
    assert m.athlete_id == ""


def test_gender_filter_excludes_other_division():
    male_roster = [_ref("Jane Example", "Jane")]
    male_roster[0].gender = "Male"
    m = match_athlete("Jane Example", "Preteen", "Female", male_roster)
    assert m.status == "not_found"


def test_override_wins_and_is_verified():
    overrides = {
        normalize_name("Alex Sample"): {
            "athlete_name_clean": "Alex Sample",
            "athlete_id": "9999",
            "gym_normalized": "Sample Ninja Warehouse",
            "state": "Texas",
        }
    }
    m = match_athlete("Alex Sample", "Preteen", "Female", ROSTER, overrides)
    assert m.status == "verified"
    assert m.athlete_id == "9999"
    assert m.source == "override"


def test_normalize_gym_uses_alias_then_falls_back_to_raw():
    aliases = {normalize_name("Grit Ninja"): GymInfo("The Grit Ninja", "", "NJ", "USA")}
    assert normalize_gym("Grit Ninja", aliases).gym_normalized == "The Grit Ninja"
    # Unknown gym keeps cleaned raw text -- we never invent details.
    unknown = normalize_gym("Mystery Ninja", aliases)
    assert unknown.gym_normalized == "Mystery Ninja"
    assert normalize_gym("", aliases).gym_normalized == ""


def test_dedupe_roster_keeps_distinct_divisions():
    # Same person across two divisions must survive as two rows so the
    # division filter can still find the right one.
    pre = _ref("Sam Twin", "Sam", "111")
    teen = RefAthlete(
        full_name="Sam Twin", first_name="Sam", athlete_id="222",
        division="Teen", gender="Female",
        full_norm=normalize_name("Sam Twin"), first_norm=normalize_name("Sam"),
    )
    out = dedupe_roster([pre, teen, _ref("Sam Twin", "Sam", "111")])
    divisions = sorted(r.division for r in out)
    assert divisions == ["Preteen", "Teen"]

    teen_match = match_athlete("Sam Twin", "Teen", "Female", out)
    assert teen_match.athlete_id == "222"


def test_load_overrides_skips_template_comment_lines(tmp_path):
    # Mirrors the committed .example: leading '#' instructions then header.
    p = tmp_path / "athlete_overrides.csv"
    p.write_text(
        "# instructions line one\n"
        "# columns below\n"
        "athlete_name_clean,athlete_id,gym_normalized\n"
        "Jane Example,1001,Example Ninja Gym\n"
    )
    overrides = load_overrides(p)
    assert normalize_name("Jane Example") in overrides
    assert overrides[normalize_name("Jane Example")]["gym_normalized"] == "Example Ninja Gym"


def test_enrich_runs_fills_columns_and_builds_tabs():
    runs = [
        {
            "athlete_name_clean": "Jane Example", "division": "Preteen",
            "gender": "Female", "gym_raw": "Grit Ninja", "city": "", "state": "",
            "date": "2026-06-19", "notes": "x",
        },
        {
            "athlete_name_clean": "Quinn", "division": "Preteen",
            "gender": "Female", "gym_raw": "", "city": "", "state": "",
            "date": "2026-06-19", "notes": "x",
        },
    ]
    aliases = {normalize_name("Grit Ninja"): GymInfo("The Grit Ninja", "Mawah", "NJ", "USA")}
    athletes, gyms = enrich_runs(runs, ROSTER, {}, aliases)

    jane, quinn = runs
    assert jane["athlete_match_status"] == "high_confidence"
    assert jane["matched_athlete_name"] == "Jane Example"
    assert jane["gym_normalized"] == "The Grit Ninja"
    assert jane["state"] == "NJ"  # backfilled from gym alias
    assert "transcript_gym" in jane["enrichment_source"]

    assert quinn["athlete_match_status"] == "ambiguous"
    assert quinn["matched_athlete_name"] == ""
    assert "ambiguous:" in quinn["notes"]

    # One gym row built; Jane present in athletes by matched name.
    assert [g["gym_normalized"] for g in gyms] == ["The Grit Ninja"]
    assert any(a["athlete_name"] == "Jane Example" for a in athletes)
