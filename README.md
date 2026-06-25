# ninjasheets

A searchable, filterable index of **World Ninja League**-style competition
videos. The unit of analysis is **one athlete run**, not one livestream — so a
parent, coach, athlete, or fan can search a name and click straight to that run
on YouTube instead of scrubbing a 2.5-hour stream.

> **Status:** Phase 1 — one-video proof of concept. Transcript-based extraction
> of athlete announcements → a reviewable spreadsheet with direct timestamp
> links.

This is an **unofficial community tooling project**. It links to public YouTube
videos and is not affiliated with WNL. See [privacy & safety](#privacy--safety).

> **How this repo is meant to be used.** The **code** is public (this repo).
> The **video config and generated spreadsheets are not** — you run the tool
> locally against your own `config/videos.yaml`, and share the resulting
> spreadsheet through private channels (e.g. a gym's parent group chat). The
> repo intentionally contains no specific video IDs, no athlete data, and no
> generated output. See [the data boundary](#what-is-and-isnt-in-this-repo).

---

## What it does (Phase 1)

For one configured video it:

1. Fetches video metadata + auto-captions (`yt-dlp`).
2. Normalizes the transcript into timestamped lines.
3. Detects athlete-announcement lines (e.g. *“Our next competitor is …”*),
   pulling candidate **name**, **gym**, and **city/state** cues.
4. Builds a YouTube link 5 seconds before each announcement.
5. Exports an `.xlsx` workbook (and a `runs.csv`) ready to review and publish
   to Google Sheets.

Every auto-extracted row ships as `unreviewed` with a `source_confidence` and
the `detected_text` that triggered it. **No athlete rows are invented.**

On a real ~2.5-hour single-division livestream, the transcript parser typically
recovers ~60 athlete runs at high confidence — enough to be immediately useful
to a coach or parent.

### What the `Runs` tab looks like (illustrative, fake names)

| athlete_name_clean | gym_raw | city | state | division | tier | stage | timestamp | ▶ link | confidence |
|---|---|---|---|---|---|---|---|---|---|
| Jane Example | Example Ninja | Springfield | OH | Preteen | Tier 2 | Stage 1 | 00:18:41 | ▶ Watch run | high |
| Alex Sample | Sample Ninjas | Madison | WI | Preteen | Tier 2 | Stage 1 | 00:21:42 | ▶ Watch run | high |
| Pat Placeholder | — | — | — | Preteen | Tier 2 | Stage 1 | 00:24:23 | ▶ Watch run | medium |

---

## Quick start

Requires [`uv`](https://docs.astral.sh/uv/). `yt-dlp` is installed as a
dependency; `ffmpeg` is **not** needed for Phase 1 (transcript-only).

```bash
uv sync

# One-time: create your local, git-ignored video config from the template
cp config/videos.example.yaml config/videos.yaml
# ...then edit config/videos.yaml with the video you want to process.

# Process a configured video → workbook + runs.csv (written under data/, local only)
uv run ninjasheets process --video-id <your_video_id>

# JSON summary (agent/automation friendly)
uv run ninjasheets process --video-id <your_video_id> --json

# List configured videos
uv run ninjasheets list-videos

# Rebuild a workbook from an edited runs.csv (after manual review)
uv run ninjasheets export --input data/processed/runs/<your_video_id>.csv \
  --output data/output/ninjasheets_reviewed.xlsx
```

Outputs (all under `data/`, which is git-ignored):

- `data/output/ninjasheets_<video_id>.xlsx` — the shareable workbook.
- `data/processed/runs/<video_id>.csv` — the canonical row data.
- `data/raw/…` — cached metadata + transcript for debugging.

---

## The output workbook

Tabs: `Start Here`, `Runs`, `Videos`, `Transcript Raw`, `Athletes`, `Gyms`,
`Corrections`, `Processing Log`.

**`Runs`** is the product. Important columns are leftmost (athlete, gym,
division, tier, stage, **▶ Watch run** link, timestamp, confidence); technical
fields (run_id, detected_text, provenance) sit to the right. The header is
frozen, autofilter is on, the run link is a clickable hyperlink, and the
confidence cell is color-coded (green/yellow/red).

`Athletes` and `Gyms` ship empty (headers only) — they are populated in Phase 2
enrichment, not faked.

---

## Sharing the spreadsheet

The product strategy is **spreadsheet first, app later** — the audience already
lives in spreadsheets and the value is the indexed data, not UI.

Because the output is generated locally, you share it directly to trusted,
private channels (a gym's parent group chat, a coaches' email thread), or via a
**link-restricted Google Sheet**:

1. **Manual import (zero setup).** Google Drive → *New → Google Sheets → File →
   Import → Upload* the `.xlsx`. Formatting, frozen header, filters, and
   hyperlinks carry over. Share to **specific people** (not "anyone with the
   link") and send it.
2. **CSV import per tab.** Upload `runs.csv` for a single always-current `Runs`
   tab; re-importing overwrites in place.

A small audience of family, friends, and the athletes themselves is the point —
keep distribution scoped to people who'd want it, not the open web.

---

## Deployment

There's intentionally **nothing hosted**. Phase 1 is a local CLI run — prove the
extraction pipeline before building anything to deploy.

Progression:

- **Now (Phase 1):** run the CLI locally → import to a restricted Google Sheet
  (or send the file directly). No hosting.
- **Phase 2 (enrichment):** athlete/gym matching (`rapidfuzz`) against a public
  source; same local-run flow.
- **Phase 3 (batch):** process many videos into one master index. If ever
  automated, a scheduled local/box job — kept private, given the audience.
- **Later (optional):** a lightweight read-only viewer, only if the spreadsheet
  proves valuable and the community wants it.

---

## What is (and isn't) in this repo

**In the repo (public):** the code, the example config
(`config/videos.example.yaml`), the extraction patterns, and the product spec.

**Never in the repo (local only, git-ignored):**

- `config/videos.yaml` — your real video targeting.
- `data/**` — all transcripts, intermediate data, and generated spreadsheets.

This keeps the public repo a showcase of *how it's built*, while the actual
spreadsheets and the specific videos they index stay off the open web and reach
only the people they're meant for.

---

## Project layout

```
config/
  videos.example.yaml        # template — copy to videos.yaml locally (git-ignored)
  extraction_patterns.yaml   # announcement / gym / location regexes (tune w/o code change)
src/ninjasheets/
  youtube.py    transcript.py    parsing.py
  pipeline.py   export.py        config.py    utils.py    cli.py
docs/product_spec.md         # full product + build spec
tests/
```

Tuning the parser for a new commentary style is a **config edit**
(`extraction_patterns.yaml`), not a code change.

---

## Privacy & safety

Many competitors are minors. Even where data is public, this project is
deliberately conservative:

- Indexes only public competition video / announcement info.
- No social handles, no precise ages (division labels only).
- No performance commentary, rankings, or subjective labels in the MVP.
- Provides a correction/removal path (the `Corrections` tab / linked form).
- Keeps generated output and specific video targeting **out of the repo**, so
  the open web gains no new pointer to these videos.
- Labeled **unofficial** unless formally approved by WNL.

---

## Development

```bash
uv run pytest        # 12 tests: timestamps, name cleaning, parser, links
```
