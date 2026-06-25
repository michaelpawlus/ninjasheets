"""ninjasheets CLI.

Agent-friendly per repo conventions: every command supports ``--json`` (JSON to
stdout, human messages to stderr) so other tools/agents can consume output.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import typer

from .config import get_video, load_videos
from .export import build_workbook
from .pipeline import RUN_COLUMNS, run_pipeline
from .utils import project_root

app = typer.Typer(
    add_completion=False,
    help="Searchable index of World Ninja League athlete runs.",
)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _write_runs_csv(runs: list[dict], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUN_COLUMNS)
        w.writeheader()
        w.writerows(runs)
    return path


@app.command("list-videos")
def list_videos(as_json: bool = typer.Option(False, "--json")):
    """List configured videos."""
    videos = load_videos()
    if as_json:
        print(json.dumps([v.__dict__ for v in videos], indent=2))
        return
    for v in videos:
        _err(f"{v.video_id}  {v.tier} | {v.division} {v.gender} | {v.stage}")


@app.command("process")
def process(
    video_id: str = typer.Option(..., "--video-id"),
    force: bool = typer.Option(False, "--force", help="Re-download raw sources."),
    output: Path = typer.Option(None, "--output", help="Workbook path (.xlsx)."),
    as_json: bool = typer.Option(False, "--json"),
):
    """Process one configured video into an .xlsx workbook + runs.csv."""
    try:
        video = get_video(video_id)
    except KeyError as e:
        payload = {"error": str(e), "code": 2}
        print(json.dumps(payload)) if as_json else _err(str(e))
        raise typer.Exit(2)

    result = run_pipeline(video, force=force)

    root = project_root()
    out_xlsx = output or (root / "data" / "output" / f"ninjasheets_{video_id}.xlsx")
    build_workbook(result, out_xlsx)
    csv_path = _write_runs_csv(
        result.runs, root / "data" / "processed" / "runs" / f"{video_id}.csv"
    )

    summary = {
        "video_id": video_id,
        "transcript_lines": len(result.transcript_lines),
        "candidate_runs": len(result.runs),
        "by_confidence": {
            c: sum(1 for r in result.runs if r["source_confidence"] == c)
            for c in ("high", "medium", "low")
        },
        "workbook": str(out_xlsx),
        "runs_csv": str(csv_path),
    }
    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        _err(f"Processed {video_id}: {summary['candidate_runs']} runs "
             f"({summary['by_confidence']}) -> {out_xlsx}")


@app.command("export")
def export(
    input_csv: Path = typer.Option(..., "--input", help="runs.csv to load."),
    output: Path = typer.Option(..., "--output", help="Workbook path (.xlsx)."),
):
    """Rebuild a workbook from an already-processed runs.csv (review-friendly)."""
    from .config import get_video
    from .pipeline import PipelineResult

    rows = list(csv.DictReader(input_csv.open()))
    if not rows:
        _err("No rows in input CSV.")
        raise typer.Exit(1)
    video = get_video(rows[0]["video_id"])
    result = PipelineResult(video, {}, [], [], rows, [])
    build_workbook(result, output)
    _err(f"Wrote {output} from {len(rows)} rows.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
