import argparse

from .config import ensure_pipeline_dirs, get_config
from .discover_fasecolda_sources import discover_sources
from .download_sources import download_sources
from .pipeline_logger import write_status
from .process_ciudades_ramos import process_ciudades_ramos
from .process_indicadores_gestion import process_indicadores_gestion
from .update_duckdb import update_duckdb
from .validate_pipeline_outputs import validate_pipeline_outputs


def run_process(config) -> int:
    print("Processing Ciudades y Ramos...")
    ciudades = process_ciudades_ramos(config)
    print(f"Processed Ciudades y Ramos rows: {len(ciudades):,}")

    print("Processing Indicadores de Gestion...")
    indicadores = process_indicadores_gestion(config)
    print(f"Processed Indicadores de Gestion rows: {len(indicadores):,}")

    write_status(
        config,
        {
            "mode": "process",
            "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
            "files_downloaded": 0,
            "files_processed": int(len(ciudades) + len(indicadores)),
            "validation_status": "not_run",
            "latest_available_period": "N/A",
            "database_status": "unchanged",
            "automation_mode": "Manual run only",
            "message": "Processed outputs were written under data/processed/fasecolda.",
        },
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Colombia Fasecolda ingestion pipeline.")
    parser.add_argument(
        "--mode",
        choices=["discover", "download", "process", "validate", "update-db", "full"],
        default="validate",
        help="Pipeline step to run.",
    )
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Allow update-db/full to replace the current DuckDB after validation passes.",
    )
    args = parser.parse_args()
    config = get_config()
    ensure_pipeline_dirs(config)

    if args.mode in ["discover", "full"]:
        print("Discovering sources...")
        sources = discover_sources(config)
        print(f"Discovery records written: {len(sources):,}")

    if args.mode in ["download", "full"]:
        print("Downloading new files...")
        manifest = download_sources(config)
        downloaded = (manifest["status"] == "downloaded").sum() if not manifest.empty else 0
        print(f"New files downloaded: {downloaded:,}")

    if args.mode in ["process", "full"]:
        run_process(config)

    if args.mode in ["validate", "full"]:
        print("Running validations...")
        report, has_errors = validate_pipeline_outputs(config, mode=args.mode)
        print(report.to_string(index=False))
        if has_errors:
            print("Validation completed with ERROR results. Database promotion is blocked.")

    if args.mode in ["update-db", "full"]:
        print("Building DuckDB candidate...")
        updated = update_duckdb(config, promote=args.promote)
        if args.promote:
            print("Promotion requested. See pipeline status for final database state.")
        else:
            print("Candidate build completed without promotion. Current demo database is unchanged.")
        return 0 if updated else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

