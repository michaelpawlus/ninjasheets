# ninjasheets Product + Build Spec

## 1. Product Summary

**Product name:** `ninjasheets`

**One-line description:** A searchable, filterable index of World Ninja League competition videos that lets athletes, parents, coaches, and gyms click directly to individual athlete runs on YouTube.

**Core promise:**

> Find any athlete's run in seconds by searching or filtering by athlete, gym, division, tier, stage, video, or competition metadata, then click a direct timestamp link to watch the run.

## 2. Background and Current State

World Ninja League competition livestreams are published as long YouTube Live recordings. A single video can contain many athlete runs. Viewers often want to find one athlete, all athletes from a gym, all runs in a division, or all runs across a weekend.

Current user behavior is fragmented:

1. Open a specific YouTube video.
2. Use YouTube/Gemini or manual transcript search to locate an athlete.
3. Prompt or search separately for each video.
4. Manually copy timestamp links.
5. Repeat for every video, stage, or division.

This is useful for one video, but it does not solve the cross-video problem.

`ninjasheets` adds value by creating a master searchable index where the unit of analysis is **one athlete run**, not one livestream video.

## 3. Target Users

### 3.1 Parents and family

Primary need: find and share a child's run quickly.

Common user stories:

- As a parent, I want to search my child's name and click directly to their run.
- As a parent, I want to share the timestamp link with grandparents or friends.
- As a parent, I do not want to scrub through a 3-hour livestream.

### 3.2 Coaches and gym owners

Primary need: review all athletes from a given gym.

Common user stories:

- As a coach, I want to filter by gym and see every athlete from our gym.
- As a coach, I want to review all Stage 1 runs from our athletes.
- As a gym owner, I want to create a social recap or send families their links.

### 3.3 Athletes

Primary need: find their own run or study others in the same division.

Common user stories:

- As an athlete, I want to find my own run quickly.
- As an athlete, I want to watch competitors in my division.
- As an athlete, I want to compare runs across stages.

### 3.4 Community members/content creators

Primary need: make highlight posts, recaps, or analysis.

Common user stories:

- As a community member, I want to find standout runs without watching every livestream.
- As a content creator, I want a reliable source of direct run links.

## 4. Product Strategy

### 4.1 Recommended first product form

Start with a **Google Sheet / Excel workbook output**, not a standalone web app.

Why:

- The audience already understands spreadsheets and filters.
- The key product value is the indexed data, not a complex UI.
- Sheets are easy to share with coaches, parents, and gyms.
- Early feedback will be about data quality and usefulness, not UI polish.
- It avoids overbuilding before the extraction pipeline is proven.

### 4.2 Later product possibilities

A lightweight web app may make sense later if the spreadsheet proves valuable.

Possible future web app features:

- Search box by athlete/gym/division.
- Gym landing pages.
- Athlete pages.
- Public correction submission.
- Embedded YouTube player.
- Multi-event archive.
- Saved filters.

The initial goal is to validate that people want the indexed data.

## 5. Scope by Phase

## Phase 1: One-video run index

### Goal

Create a spreadsheet for one specific video with athlete names and clickable timestamp links.

### Starting video

- **Video URL:** `https://www.youtube.com/live/EXAMPLE_VIDEO_ID`
- **Video ID:** `EXAMPLE_VIDEO_ID`
- **Event/video:** Tier 2 | Preteen Female | Stage 1 | Season 11 World Championships
- **Known context:** This video has a transcript, and athletes are announced at the start of each run.

### Success criteria

A user can:

1. Open the spreadsheet.
2. Search for an athlete name.
3. Click a direct YouTube timestamp link.
4. Land close enough to the start of that athlete's run to watch comfortably.

### Phase 1 required columns

- `run_id`
- `event_name`
- `season`
- `video_id`
- `video_url`
- `video_title`
- `tier`
- `division`
- `gender`
- `stage`
- `wave`
- `run_order_in_wave`
- `run_order_overall`
- `athlete_name_raw`
- `athlete_name_clean`
- `timestamp_seconds`
- `timestamp_hhmmss`
- `youtube_run_url`
- `start_source`
- `source_confidence`
- `review_status`
- `notes`

### Phase 1 non-goals

- Perfect gym matching.
- Full multi-video batch processing.
- Public web app.
- Performance scoring or results analysis.
- Spoiler-heavy leaderboard functionality.

## Phase 2: Athlete/gym enrichment

### Goal

Join athlete rows to WNL/NinjaWorks-style athlete data so that the sheet can include gym, city, state, and possibly athlete ID.

The highest-value field is `gym` because it enables the key coach/gym-owner workflow:

> Filter by gym and see every athlete run from that gym.

### Success criteria

A user can:

1. Filter by `gym_normalized`.
2. See all matched athlete runs from that gym.
3. Trust the matches because each row has a match confidence/status.

### Phase 2 required enrichment columns

- `athlete_id`
- `athlete_match_status`
- `athlete_match_score`
- `matched_athlete_name`
- `gym_raw`
- `gym_normalized`
- `city`
- `state`
- `country`
- `enrichment_source`
- `enrichment_review_status`

### Phase 2 risks

- Gym affiliation may not be available publicly.
- Names may be duplicated.
- Athlete records may use nicknames, abbreviations, or misspellings.
- Gym names may be inconsistent.
- Some athletes may have no gym listed.
- Some data may require login or may not be appropriate to scrape.

### Phase 2 principle

Do not silently overmatch.

Use explicit confidence labels:

- `verified`
- `high_confidence`
- `medium_confidence`
- `low_confidence`
- `needs_review`
- `not_found`
- `ambiguous`

## Phase 3: Multi-video master index

### Goal

Process many WNL videos into one master dataset where each row is one athlete run.

### Success criteria

A user can:

1. Filter to one gym and see all athlete runs across videos, days, divisions, stages, and competitions.
2. Filter by tier/division/gender/stage.
3. Search by athlete name.
4. Click directly to each run.

### Phase 3 required additions

- Batch video config.
- Video metadata extraction.
- Title parser.
- Event schedule parser or manual event config.
- Repeatable transcript extraction.
- Repeatable timestamp extraction.
- Human review workflow.
- Master workbook export.
- Optional Google Sheets publishing.

## 6. Important Domain Notes

### 6.1 Run orders are not reliable as long-term sources

Run orders may exist before and during a competition, but they can disappear or update as athletes complete runs. In live competition use, this is useful because it shows who remains. For historical indexing, it creates a reliability issue.

Implication:

- Do not design the product to depend on run orders always being available after the event.
- Treat persisted run orders as a helpful source when available, not the only source of truth.
- Archive or snapshot run orders if they are available at processing time.
- Store provenance for every row.

### 6.2 Videos may include partial run-order screens

At the beginning of many videos, the stream may show a partial run order. However, competitions may run in waves, so the initial screen might only show Wave 1.

Implication:

- OCR on initial run-order screens can help, but it may not capture all waves.
- A robust approach should scan for later run-order screens or use transcript announcements.
- The pipeline should support multiple candidate sources for athlete order.

### 6.3 Athlete announcements are highly valuable

For the starting video, athletes are announced at the start of each run. This means transcript-based extraction may be sufficient for Phase 1.

Implication:

- Transcript parsing should be the first extraction method for this video.
- The pipeline should search for announcement patterns and produce candidate athlete/timestamp rows.

### 6.4 Timestamp definition must be explicit

The product should define what timestamp means.

Recommended definition:

> `timestamp_seconds` should point to a few seconds before the athlete's run begins, ideally at or just before the athlete announcement.

Recommended default:

- `detected_announcement_time_seconds` = time where the transcript/OCR/audio identifies the athlete.
- `timestamp_seconds` = `max(0, detected_announcement_time_seconds - 5)`.

This gives the viewer context and reduces the risk of landing after the start.

## 7. Data Model

## 7.1 Core table: `runs`

Each row represents one athlete run in one video.

| Column | Type | Required | Description |
|---|---:|---:|---|
| `run_id` | string | yes | Stable unique ID. Suggested format: `{video_id}_{run_order_overall}` or UUID. |
| `event_name` | string | yes | Example: `Season 11 World Championships`. |
| `season` | string | yes | Example: `Season 11`. |
| `competition_name` | string | optional | Example: `World Championships`. |
| `video_id` | string | yes | YouTube video ID. |
| `video_url` | string | yes | Original YouTube URL. |
| `video_title` | string | yes | YouTube title. |
| `tier` | string | yes | Example: `Tier 2`. |
| `division` | string | yes | Example: `Preteen`. |
| `gender` | string | yes | Example: `Female`. |
| `stage` | string | yes | Example: `Stage 1`. |
| `course` | string | optional | Example: `Stage 1 Tall B`. |
| `date` | date/string | optional | Competition date if known. |
| `wave` | integer/string | optional | Wave number if available. |
| `run_order_in_wave` | integer | optional | Order inside wave. |
| `run_order_overall` | integer | optional | Overall inferred order in video. |
| `athlete_name_raw` | string | yes | Name exactly as extracted from transcript/OCR/source. |
| `athlete_name_clean` | string | yes | Normalized display name. |
| `timestamp_seconds` | integer | yes | Link timestamp, ideally 5 seconds before run/announcement. |
| `timestamp_hhmmss` | string | yes | Human-readable timestamp. |
| `youtube_run_url` | string | yes | `https://youtu.be/{video_id}?t={timestamp_seconds}`. |
| `detected_text` | string | optional | Transcript/OCR text that triggered the row. |
| `start_source` | string | yes | `transcript`, `manual`, `ocr_overlay`, `ocr_run_order`, `speech_to_text`, `estimated`. |
| `source_confidence` | string | yes | `high`, `medium`, `low`. |
| `review_status` | string | yes | `unreviewed`, `needs_review`, `reviewed`, `verified`. |
| `notes` | string | optional | Free-text QA notes. |

## 7.2 Table: `videos`

Each row represents one source YouTube video.

| Column | Type | Required | Description |
|---|---:|---:|---|
| `video_id` | string | yes | YouTube video ID. |
| `video_url` | string | yes | YouTube URL. |
| `video_title` | string | yes | Original title. |
| `event_name` | string | yes | Event name. |
| `season` | string | optional | Season. |
| `tier` | string | optional | Tier parsed from title/config. |
| `division` | string | optional | Division parsed from title/config. |
| `gender` | string | optional | Gender parsed from title/config. |
| `stage` | string | optional | Stage parsed from title/config. |
| `course` | string | optional | Course location if known. |
| `scheduled_start` | string | optional | Schedule time if known. |
| `scheduled_end` | string | optional | Schedule time if known. |
| `transcript_available` | boolean | yes | Whether transcript/captions were retrieved. |
| `processing_status` | string | yes | `not_started`, `processed`, `needs_review`, `failed`. |
| `source_notes` | string | optional | Notes about run order, schedule, etc. |

## 7.3 Table: `athletes`

Each row represents one matched athlete profile, if available.

| Column | Type | Required | Description |
|---|---:|---:|---|
| `athlete_id` | string | optional | WNL/NinjaWorks athlete ID if available. |
| `athlete_name` | string | yes | Display name. |
| `athlete_name_normalized` | string | yes | Normalized matching key. |
| `gym_raw` | string | optional | Gym name from source. |
| `gym_normalized` | string | optional | Cleaned gym name. |
| `city` | string | optional | City. |
| `state` | string | optional | State/province. |
| `country` | string | optional | Country. |
| `source_url` | string | optional | Source profile/result URL. |
| `source_type` | string | optional | Example: `official_index`, `results_page`, `manual`. |
| `last_updated` | string | optional | Date processed. |

## 7.4 Table: `gyms`

Each row represents a normalized gym/facility.

| Column | Type | Required | Description |
|---|---:|---:|---|
| `gym_id` | string | optional | Stable internal gym ID. |
| `gym_raw` | string | yes | Raw observed gym name. |
| `gym_normalized` | string | yes | Canonical gym name. |
| `city` | string | optional | City. |
| `state` | string | optional | State/province. |
| `country` | string | optional | Country. |
| `source_url` | string | optional | Source URL. |
| `notes` | string | optional | Alias or review notes. |

## 7.5 Table: `corrections`

Rows submitted by users or reviewers.

| Column | Type | Required | Description |
|---|---:|---:|---|
| `submitted_at` | datetime | yes | Timestamp. |
| `submitter_name` | string | optional | Optional. |
| `submitter_email` | string | optional | Optional. |
| `run_id` | string | optional | Affected run ID. |
| `field` | string | yes | Field being corrected. |
| `current_value` | string | optional | Current value. |
| `suggested_value` | string | yes | Suggested correction. |
| `evidence` | string | optional | Explanation/link. |
| `status` | string | yes | `new`, `accepted`, `rejected`, `needs_followup`. |
| `reviewer_notes` | string | optional | Internal note. |

## 8. Workbook / Google Sheet Layout

Recommended tabs:

1. `Start Here`
2. `Runs`
3. `Videos`
4. `Transcript Raw`
5. `Athletes`
6. `Gyms`
7. `Corrections`
8. `Processing Log`

## 8.1 `Start Here`

Purpose: Explain the sheet to users.

Recommended contents:

- Product title: `ninjasheets`
- Short description.
- Coverage note.
- Last updated timestamp.
- Instructions:
  - Search athlete name.
  - Filter by gym/division/stage.
  - Click `YouTube Run Link`.
  - Submit corrections using linked form.
- Disclaimer:
  - Unofficial community index.
  - Not affiliated with WNL unless an official relationship exists.
  - Links point to public YouTube videos.

## 8.2 `Runs`

This is the main product tab.

Required UX details:

- Freeze header row.
- Enable filters.
- Keep the most important columns leftmost:
  - Athlete
  - Gym
  - Division
  - Tier
  - Stage
  - YouTube Run Link
  - Timestamp
  - Confidence
- Hide or move technical columns to the right.
- Use confidence/review status columns to avoid false certainty.

Recommended first columns:

1. `athlete_name_clean`
2. `gym_normalized`
3. `division`
4. `gender`
5. `tier`
6. `stage`
7. `wave`
8. `run_order_overall`
9. `timestamp_hhmmss`
10. `youtube_run_url`
11. `source_confidence`
12. `review_status`
13. `notes`

## 8.3 `Transcript Raw`

Purpose: Store transcript lines before parsing.

Recommended columns:

- `video_id`
- `start_seconds`
- `duration_seconds`
- `text`
- `text_normalized`
- `candidate_athlete_name`
- `candidate_confidence`
- `parser_notes`

## 8.4 `Processing Log`

Purpose: Make the pipeline auditable.

Recommended columns:

- `run_datetime`
- `video_id`
- `step`
- `status`
- `rows_created`
- `warnings`
- `errors`
- `notes`

## 9. Extraction Pipeline

## 9.1 Overview

The pipeline should accept one or more YouTube video URLs and produce:

1. A normalized video metadata table.
2. A raw transcript table when available.
3. Candidate athlete run rows.
4. Timestamped YouTube links.
5. Optional athlete/gym enrichment.
6. An Excel workbook and/or Google Sheet.

## 9.2 Recommended processing flow for Phase 1

### Step 1: Load config

Use a manually curated config file for the first video.

Example `videos.yaml`:

```yaml
videos:
  - video_id: EXAMPLE_VIDEO_ID
    video_url: "https://www.youtube.com/live/EXAMPLE_VIDEO_ID"
    event_name: "Season 11 World Championships"
    season: "Season 11"
    tier: "Tier 2"
    division: "Preteen"
    gender: "Female"
    stage: "Stage 1"
    course: "Stage 1 Tall B"
    timestamp_buffer_seconds: 5
    expected_extraction_methods:
      - transcript
      - manual_review
```

Reasoning:

- Avoid over-relying on title parsing for the first version.
- The config creates a reliable source of metadata.
- Later phases can add automatic title parsing.

### Step 2: Fetch video metadata

Use CLI/tooling available to the coding agent to retrieve:

- video title
- video ID
- duration
- available subtitles/captions
- automatic captions if present

Suggested tools:

- `yt-dlp` for metadata/subtitle listing/downloading.
- YouTube transcript tooling if available.
- Fallback to manual transcript export if necessary.

Implementation note:

- Store all raw metadata in `data/raw/video_metadata/{video_id}.json`.
- Do not rely only on parsed display strings; keep raw outputs for debugging.

### Step 3: Fetch transcript/captions

For videos with transcripts:

- Download subtitles or automatic captions.
- Convert transcript to a normalized dataframe.
- Preserve original text and timing.

Required output columns:

- `video_id`
- `start_seconds`
- `duration_seconds`
- `end_seconds`
- `text_raw`
- `text_normalized`

Store as:

- `data/raw/transcripts/{video_id}.json` or `.vtt`
- `data/processed/transcripts/{video_id}.csv`

### Step 4: Parse candidate athlete announcements

Use transcript pattern matching to identify lines likely to announce an athlete.

Possible announcement patterns:

- `next up ...`
- `next athlete ...`
- `up next ...`
- `on the course ...`
- `we have ...`
- `from [gym] ...`
- `representing ...`
- `[athlete name] from [gym]`
- `this is [athlete name]`

The exact phrases should be discovered by inspecting the first transcript.

The parser should create candidate rows with:

- candidate name
- candidate timestamp
- surrounding transcript context
- confidence score
- reason/pattern matched

Recommended context window:

- Include transcript text from 10 seconds before to 20 seconds after the candidate announcement.

This helps with human review and debugging.

### Step 5: Clean and normalize names

For each candidate:

- Remove filler words.
- Remove common announcement phrases.
- Strip punctuation.
- Normalize whitespace.
- Title-case carefully.
- Preserve raw name separately.

Do not over-clean names. The raw text should always be retained.

### Step 6: Deduplicate candidate announcements

The announcer may say the athlete name multiple times.

Deduplication rules:

- Collapse candidates with the same normalized athlete name within a short time window, e.g. 30-60 seconds.
- Prefer the earliest timestamp that plausibly introduces the run.
- Keep alternate mentions in a debug table if useful.

### Step 7: Create timestamp links

For each candidate:

```text
timestamp_seconds = max(0, detected_start_seconds - timestamp_buffer_seconds)
youtube_run_url = "https://youtu.be/{video_id}?t={timestamp_seconds}"
```

Also create `timestamp_hhmmss`.

Example conversion:

- `3725` seconds -> `01:02:05`

### Step 8: Export workbook

Create an `.xlsx` workbook matching the tabs in this spec.

Recommended Python libraries:

- `pandas`
- `openpyxl`
- optionally `xlsxwriter`

Required workbook features:

- Frozen headers.
- Filters on core tabs.
- Reasonable column widths.
- Clickable hyperlinks.
- Status fields.
- No fake populated data.

## 10. Fallback Strategies for Videos Without Transcripts

Videos without YouTube transcripts are **not off the table**. They require fallback extraction methods.

## 10.1 Fallback A: Manual timestamping

Most reliable fallback.

Workflow:

1. Use known video metadata and any available athlete/order source.
2. Reviewer watches/scrubs video.
3. Reviewer records athlete name and timestamp.
4. Pipeline converts entries into final sheet.

Pros:

- High accuracy.
- Fast to implement.
- Good for initial proof of concept.

Cons:

- Does not scale well without volunteer/community review.

Recommended support:

Create a `manual_runs.csv` template:

```csv
video_id,athlete_name_clean,timestamp_hhmmss,wave,run_order_overall,notes
EXAMPLE_VIDEO_ID,Jane Example,00:12:34,1,1,Manual timestamp from announcement
```

## 10.2 Fallback B: OCR on athlete name overlays

If the stream shows athlete names on screen, extract video frames and OCR overlays.

Workflow:

1. Sample frames every N seconds, e.g. every 1-3 seconds.
2. Crop likely lower-third/name-card region if consistent.
3. Run OCR.
4. Detect new names.
5. Convert first appearance of name into timestamp candidate.
6. Human review.

Potential tools:

- `ffmpeg` for frame extraction.
- `tesseract` or `easyocr` for OCR.
- OpenCV for cropping/preprocessing.

Pros:

- Does not require transcript.
- Can work well if graphics are consistent.

Cons:

- Sensitive to layout, compression, fonts, motion, and lighting.
- May need per-video or per-stream layout tuning.

## 10.3 Fallback C: OCR on run-order screens

If the video displays a run-order screen at the start of each wave, OCR it.

Important caveat:

- The first displayed run order may only contain Wave 1.
- Later wave screens must be scanned too.

Workflow:

1. Detect frames that look like run-order tables.
2. OCR names from those frames.
3. Assign wave number based on appearance time or manual review.
4. Use as athlete list/order.
5. Combine with transcript/audio/OCR overlay/manual timestamps.

Pros:

- Can recover athlete order even if official run order disappeared.

Cons:

- Does not always provide exact run start timestamp.
- Requires scan across the full video for later wave screens.

## 10.4 Fallback D: Speech-to-text from audio

If YouTube has no transcript, download/extract audio and run speech-to-text.

Workflow:

1. Extract audio using `ffmpeg` or video tooling.
2. Run local or cloud speech-to-text.
3. Parse generated transcript using the same transcript parser.

Potential tools:

- OpenAI Whisper / whisper.cpp.
- Cloud transcription services if available.

Pros:

- Preserves transcript-based pipeline.

Cons:

- Competition audio may be noisy.
- Names may be transcribed poorly.
- Cost/time may increase.

## 10.5 Fallback E: Estimated timing from sequence

Use only as a review accelerator, not a final source.

Workflow:

1. Identify first few confirmed athlete timestamps.
2. Estimate expected intervals.
3. Generate approximate candidate timestamps.
4. Human verifies.

Pros:

- Speeds review.

Cons:

- Too error-prone for final links without verification.

## 11. Confidence Scoring

Every row should communicate data confidence.

## 11.1 Recommended `source_confidence` values

- `high`: clear transcript or OCR match, timestamp verified or highly likely.
- `medium`: likely athlete announcement but transcript/OCR has uncertainty.
- `low`: weak match, estimated timestamp, or ambiguous name.

## 11.2 Recommended `review_status` values

- `unreviewed`: generated by automation, not checked.
- `needs_review`: automation detected a likely issue.
- `reviewed`: a person checked it but not necessarily official.
- `verified`: highly confident after manual check or multiple sources agree.

## 11.3 Suggested automatic scoring factors

Positive factors:

- Transcript line contains an announcement phrase.
- Name appears in expected run order.
- Name appears in OCR overlay near the same timestamp.
- Candidate appears after previous athlete and before next athlete.
- Candidate has clean capitalization/name shape.

Negative factors:

- Candidate text is short or generic.
- Candidate looks like a commentator, judge, sponsor, or gym rather than athlete.
- Same name appears many times far apart.
- Timestamp is too close to another candidate.
- Transcript contains obvious transcription errors.

## 12. Athlete/Gym Matching Design

## 12.1 Matching principles

Use fuzzy matching, but do not hide uncertainty.

Recommended matching fields:

- athlete name
- division
- gender
- tier
- event
- state/country if available
- gym if already extracted from transcript

Recommended tools:

- `rapidfuzz` for local fuzzy string matching.
- Manual override table for ambiguous athletes.

## 12.2 Matching outputs

Each match should produce:

- `athlete_id`
- `matched_athlete_name`
- `athlete_match_score`
- `athlete_match_status`
- `gym_raw`
- `gym_normalized`
- `city`
- `state`
- `country`
- `enrichment_source`

## 12.3 Ambiguity handling

Rules:

- If exactly one high-confidence match exists, auto-fill.
- If multiple plausible matches exist, mark `ambiguous`.
- If no good match exists, mark `not_found`.
- If a human corrects a match, store it in an override table and apply it in future runs.

Suggested override file:

```csv
athlete_name_clean,division,gender,athlete_id,gym_normalized,reviewer_notes
Jane Example,Preteen,Female,123456,Example Ninja Gym,Confirmed by coach
```

## 13. File and Repository Structure

Recommended repository:

```text
ninjasheets/
  README.md
  pyproject.toml
  .gitignore
  config/
    videos.yaml
    extraction_patterns.yaml
    gym_aliases.csv
    athlete_overrides.csv
  data/
    raw/
      video_metadata/
      transcripts/
      subtitles/
      frames/
      ocr/
    processed/
      transcripts/
      candidate_runs/
      runs/
      athletes/
      gyms/
    output/
      ninjasheets_mvp_one_video.xlsx
      ninjasheets_master.xlsx
  notebooks/
    01_inspect_transcript.ipynb
    02_review_candidates.ipynb
  src/
    ninjasheets/
      __init__.py
      config.py
      youtube.py
      transcript.py
      ocr.py
      parsing.py
      matching.py
      export.py
      review.py
      utils.py
  tests/
    test_timestamp.py
    test_name_cleaning.py
    test_transcript_parser.py
    test_youtube_links.py
  scripts/
    process_video.py
    process_batch.py
    export_workbook.py
```

## 14. CLI Design

Recommended commands:

```bash
# Process one video from config
python scripts/process_video.py --video-id EXAMPLE_VIDEO_ID

# Process all configured videos
python scripts/process_batch.py --config config/videos.yaml

# Export workbook only from processed data
python scripts/export_workbook.py --input data/processed/runs/runs.csv --output data/output/ninjasheets_master.xlsx

# Run transcript inspection helper
python scripts/process_video.py --video-id EXAMPLE_VIDEO_ID --write-debug-context
```

## 15. Suggested Implementation Milestones

## Milestone 0: Repo setup

Deliverables:

- Repo created.
- Config file with the initial video.
- Basic README.
- Dependency setup.
- Output folder structure.

Done when:

- A developer can run a hello-world pipeline command.

## Milestone 1: Workbook scaffold

Deliverables:

- Code creates a workbook with required tabs.
- `Videos` tab populated from config.
- `Runs` tab has expected schema and filters.

Done when:

- Running `export_workbook.py` creates a valid `.xlsx` file.

## Milestone 2: Transcript retrieval

Deliverables:

- Code retrieves transcript/captions for the initial video if available.
- Transcript saved raw and normalized.
- `Transcript Raw` tab populated.

Done when:

- The transcript appears in the workbook with timestamped lines.

## Milestone 3: Candidate athlete extraction

Deliverables:

- Parser identifies likely athlete announcement lines.
- Candidate run rows created.
- YouTube timestamp links generated.

Done when:

- `Runs` tab contains candidate athlete rows with links.

## Milestone 4: Review workflow

Deliverables:

- Rows have `source_confidence` and `review_status`.
- Debug context included for each candidate.
- Manual corrections can be applied from CSV.

Done when:

- A human can review and correct the first video without editing code.

## Milestone 5: Athlete/gym enrichment prototype

Deliverables:

- Import an athlete/gym source file or scrapeable public source if appropriate.
- Fuzzy match names.
- Add gym/city/state fields.
- Mark ambiguous matches.

Done when:

- At least a sample set of athletes has gym data with confidence labels.

## Milestone 6: Batch processing

Deliverables:

- Multiple videos in config.
- Master `Runs` table across videos.
- Workbook export scales to multiple videos.

Done when:

- Filtering by gym shows runs across multiple videos.

## 16. Acceptance Criteria for the Initial Video

The initial video proof of concept is complete when:

1. The workbook includes at least one populated `Videos` row for `EXAMPLE_VIDEO_ID`.
2. Transcript lines are stored in `Transcript Raw` if available.
3. Candidate athlete rows are created in `Runs`.
4. Every candidate row has a clickable YouTube link.
5. Every candidate row has a confidence and review status.
6. Timestamp links open near athlete announcements or run starts.
7. The workbook is usable with filters.
8. No rows are presented as verified unless they were checked.
9. The output can be regenerated by running a script.

## 17. Quality Assurance Checklist

For each processed video:

- [ ] Video metadata is correct.
- [ ] Video ID is correct.
- [ ] Tier/division/gender/stage are correct.
- [ ] Transcript exists or fallback method is documented.
- [ ] Candidate rows were generated.
- [ ] Duplicate athlete announcements were handled.
- [ ] Timestamp links open correctly.
- [ ] Names are not obviously commentator/judge/sponsor names.
- [ ] Source confidence is populated.
- [ ] Review status is populated.
- [ ] Any uncertain rows are marked `needs_review`.
- [ ] Workbook filters work.
- [ ] Hyperlinks are clickable.

## 18. Privacy, Safety, and Community Considerations

Many competitors are minors. Even if video and run-order information is public, the product should be conservative.

Guidelines:

- Only index public competition-related information.
- Do not add personal social media handles.
- Do not add precise ages unless already officially published and necessary.
- Prefer division labels over exact age.
- Do not include performance commentary in the MVP.
- Avoid shaming, rankings, or subjective labels.
- Include a correction/removal request path.
- Label the project as unofficial unless formally approved.

Recommended disclaimer:

> ninjasheets is an unofficial community-created viewing index. It links to public competition videos and is intended to help families, athletes, coaches, and gyms find runs more easily. Please submit corrections or removal requests using the correction form.

## 19. Open Questions

1. Can the coding agent retrieve the transcript for `EXAMPLE_VIDEO_ID` using available tools?
2. What exact announcement phrases appear in the transcript?
3. Does the transcript consistently capture athlete names?
4. Are gyms announced in the audio or only athlete names?
5. Does the video show athlete name overlays?
6. Does the video show run-order screens at the start of every wave?
7. Is a persistent official run order available anywhere after the event?
8. Is athlete/gym data publicly accessible in a structured way?
9. How many videos need to be processed for the first public release?
10. Should the public artifact be Excel, Google Sheets, or both?

## 20. Recommended First Task for Coding Agent

Use the following task as the first coding-agent prompt:

> Build a Python prototype for `ninjasheets` that processes the YouTube video `https://www.youtube.com/live/EXAMPLE_VIDEO_ID` / video ID `EXAMPLE_VIDEO_ID`. The goal is to retrieve any available transcript/captions, normalize timestamped transcript lines, detect candidate athlete announcement lines, generate YouTube timestamp links with a 5-second buffer, and export an Excel workbook with tabs `Start Here`, `Runs`, `Videos`, `Transcript Raw`, `Athletes`, `Gyms`, `Corrections`, and `Processing Log`. Do not invent athlete rows. Mark generated rows as `unreviewed` and include source confidence and detected transcript text for review. Use config-driven video metadata for Tier 2, Preteen Female, Stage 1, Season 11 World Championships. Create a repeatable script and save raw outputs for debugging.

## 21. Recommended Coding Agent Guardrails

Tell the coding agent:

- Do not hardcode all logic for only one video.
- It is fine to manually configure the first video's metadata.
- Preserve raw transcript/OCR data.
- Do not invent athlete names.
- Treat all auto-extracted rows as unreviewed.
- Include confidence and provenance fields.
- Make output easy to review in Excel/Google Sheets.
- Design with batch processing in mind, but do not build a full app yet.

## 22. Product Definition of Done for MVP

The MVP is done when a parent or coach can open a spreadsheet, filter/search, and click directly to athlete runs for at least one video with enough accuracy to be useful.

A stronger MVP is done when a coach can filter by gym and see all athletes from their gym for one competition subset.

A version 1 product is done when the same system can process multiple videos into a master index and accept corrections without requiring code changes.
