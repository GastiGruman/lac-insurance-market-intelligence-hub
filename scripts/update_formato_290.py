from __future__ import annotations

import sys
import argparse
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.formato_290_pipeline import run_update


def main() -> int:
    parser = argparse.ArgumentParser(description="Update SFC Formato 290 data.")
    parser.add_argument("--from-latest-raw", action="store_true", help="Resume processing from the latest raw CSV in data/raw/formato_290.")
    parser.add_argument("--file", type=str, default=None, help="Process a specific local raw CSV file.")
    args = parser.parse_args()

    try:
        status = run_update(from_latest_raw=args.from_latest_raw, raw_file=args.file)
    except Exception as exc:
        print(f"Formato 290 update failed: {type(exc).__name__}: {exc!r}")
        print(traceback.format_exc())
        return 1
    print("Formato 290 update completed.")
    for key, value in status.items():
        print(f"- {key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
