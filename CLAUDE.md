# ninjasheets — agent guide

Searchable index of World Ninja League athlete runs. The unit of analysis is
**one athlete run**, not one livestream video. Phase 1 (current) extracts
candidate athlete announcements from a YouTube transcript and exports a
reviewable spreadsheet with direct timestamp links.

## The data boundary (read first)

This is a **public, code-only** repo. It must never contain:

- **Real video targeting** — `config/videos.yaml` is git-ignored. The committed
  template is `config/videos.example.yaml`. Do not commit real video IDs/URLs.
- **Generated output or athlete data** — everything under `data/` is
  git-ignored. The `.xlsx`/`.csv` are generated locally and shared only to
  private channels (e.g. a gym's parent group chat, a people-restricted Google
  Sheet). They never go in the repo, public or private.
- **Real names** — competitors are minors. Tests and docs use synthetic names
  (`Jane Example`, `Alex Sample`, `Quinn`). Before committing, sweep for real
  data: `git diff --cached -G '<real-id-or-name>'`.

Rationale: the open web should gain no new pointer to these videos. Keep the
showcase about *how it's built*; keep the actual index local.

## Run it

Uses `uv`. `yt-dlp` is a dependency; `ffmpeg` is NOT needed for Phase 1.

```bash
uv sync
cp config/videos.example.yaml config/videos.yaml   # one-time; edit with a real video
uv run ninjasheets process --video-id <id>          # → data/output/*.xlsx + data/processed/runs/*.csv
uv run ninjasheets process --video-id <id> --json   # machine-readable summary
uv run ninjasheets list-videos
uv run ninjasheets export --input <runs.csv> --output <out.xlsx>   # rebuild after manual review
uv run pytest                                        # 21 tests
```

## Architecture

`src/ninjasheets/`: `youtube.py` (yt-dlp metadata/transcript) → `transcript.py`
(json3 → normalized lines) → `parsing.py` (announcement detection, name
cleaning, gym/location cues, dedup, confidence) → `pipeline.py` (orchestrate →
run rows) → `enrichment.py` (Phase 2: rapidfuzz athlete match + gym
normalization) → `export.py` (8-tab .xlsx). `cli.py` is the Typer entrypoint
(`--json` on commands per repo conventions). `config.py` loads `videos.yaml` +
`extraction_patterns.yaml`.

**Phase 2 enrichment (`enrichment.py`):** matches each run's name against a
reference roster — the local sibling `WNL-Athlete-Video-Index` SQLite DB
(`../WNL-Athlete-Video-Index/...`, override via `--athlete-index` /
`NINJASHEETS_ATHLETE_INDEX_DB`) plus its `known_athletes.json` — with explicit
confidence labels (`verified`/`high_confidence`/`medium_confidence`/
`low_confidence`/`ambiguous`/`not_found`); never overmatches. Gyms normalize via
`config/gym_aliases.csv`; manual `config/athlete_overrides.csv` (git-ignored;
synthetic `.example` committed) yields `verified` and persists across runs. The
index has no gym column today, but the roster loader introspects for one, so a
matched athlete inherits an index gym automatically if/when it's added.

**Tune the parser via config, not code:** announcement/gym/location regexes live
in `config/extraction_patterns.yaml`. Patterns use scoped `(?i:...)` flags so
trigger words are case-insensitive while names/proper-nouns stay Title Case
(this both finds names in lowercased captions and stops a name at the sentence
boundary). Do NOT add a global `IGNORECASE`.

## Guardrails (from the spec)

- Never invent athlete rows. Every auto row ships `unreviewed` with
  `source_confidence` and the `detected_text` that triggered it.
- Preserve raw transcript/metadata under `data/raw/` for debugging.
- Confidence: `high`/`medium`/`low`; review: `unreviewed` → `needs_review` →
  `reviewed` → `verified`. Don't present anything as `verified` unmanually.
- Privacy: no social handles, no precise ages (division labels only), no
  rankings/commentary in the MVP, always provide a correction/removal path.

## WSL2 note

Generate on the WSL side, then copy to Windows to open/share (opening the .xlsx
directly over `\\wsl.localhost` can hit Excel file-lock quirks):
`cp data/output/<file>.xlsx /mnt/c/Users/<user>/Downloads/`. See issue #5 for a
planned `--open` flag.

## Next steps

See GitHub issues: Phase 2 enrichment (#1, **done**), Phase 3 batch/master (#2),
Sheets publishing (#3), corrections workflow (#4), `--open` (#5), parser quality
(#6), transcript-less fallbacks (#7). Phase 2 match coverage scales with the
reference roster: add more `competition_athletes` rows to the index (ideally with
a gym column) to lift athlete/gym fill-in on future videos.
