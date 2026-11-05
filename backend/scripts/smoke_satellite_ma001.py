"""Opt-in live Earth Engine smoke test for the MA-001 satellite path.

Run this script from ``backend`` after configuring Earth Engine credentials.
It deliberately disables overlay generation and prints only observation
metadata; credential contents and paths are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.services.satellite_service import fetch_indices


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def _run(args: argparse.Namespace) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    plot_path = repo_root / "docs" / "samples" / "ma001.geojson"
    geojson = json.loads(plot_path.read_text(encoding="utf-8"))

    project = settings.gee_project_id
    credentials_configured = bool(settings.gee_credentials_path)
    credentials_visible = bool(settings.gee_credentials_path and Path(settings.gee_credentials_path).is_file())

    print(f"plot=MA-001 geometry={plot_path}")
    print(f"gee_project_configured={bool(project)} expected_project={project == 'qatra-satellite-research'}")
    print(f"credentials_configured={credentials_configured} credentials_file_visible={credentials_visible}")
    if not project:
        print("result=configuration_error reason=gee_project_id_missing")
        return 2

    observation = await fetch_indices(
        geojson=geojson,
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        generate_overlay=False,
    )
    result = asdict(observation)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if observation.ndvi is not None else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", help="Optional inclusive ISO date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Optional inclusive ISO date (YYYY-MM-DD)")
    args = parser.parse_args()
    try:
        return asyncio.run(_run(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"result=configuration_error reason={type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
