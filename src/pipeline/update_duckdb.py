import shutil
from datetime import datetime

import duckdb
import pandas as pd

from .config import PipelineConfig, ensure_pipeline_dirs
from .compare_candidate_database import compare_databases
from .pipeline_logger import append_event, write_status
from .validate_pipeline_outputs import validate_pipeline_outputs


def _load_processed_table(path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def build_candidate_database(config: PipelineConfig) -> bool:
    ensure_pipeline_dirs(config)
    if not config.current_db_path.exists():
        append_event(config, "update_db", "ERROR", "Current DuckDB snapshot is missing; candidate cannot be built.")
        return False

    if config.candidate_db_path.exists():
        config.candidate_db_path.unlink()
    shutil.copy2(config.current_db_path, config.candidate_db_path)

    ciudades = _load_processed_table(config.processed_dir / "ciudades_ramos_normalized.csv")
    indicadores = _load_processed_table(config.processed_dir / "indicadores_gestion_normalized.csv")
    conn = duckdb.connect(str(config.candidate_db_path))
    try:
        if not ciudades.empty:
            conn.execute("CREATE OR REPLACE TABLE pipeline_ciudades_ramos_normalized AS SELECT * FROM ciudades")
        if not indicadores.empty:
            conn.execute("CREATE OR REPLACE TABLE pipeline_indicadores_gestion_normalized AS SELECT * FROM indicadores")
    finally:
        conn.close()

    append_event(
        config,
        "update_db",
        "PASS",
        "Candidate DuckDB built from current snapshot with pipeline audit tables. Current database is unchanged.",
    )
    return True


def promote_candidate_database(config: PipelineConfig) -> bool:
    comparison = compare_databases()
    if comparison.get("recommendation") != "Promote now":
        append_event(
            config,
            "promote_db",
            "ERROR",
            f"Candidate comparison recommendation is {comparison.get('recommendation')}; current DuckDB was not replaced.",
        )
        write_status(
            config,
            {
                "mode": "update-db",
                "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
                "files_downloaded": 0,
                "files_processed": 0,
                "validation_status": "WARNING",
                "latest_available_period": "N/A",
                "database_status": "promotion_blocked",
                "automation_mode": "Manual run only",
                "message": "Candidate comparison did not recommend promotion. Existing demo database remains unchanged.",
            },
        )
        return False

    report, has_errors = validate_pipeline_outputs(config, mode="update-db")
    if has_errors:
        append_event(config, "promote_db", "ERROR", "Validation errors found; current DuckDB was not replaced.")
        write_status(
            config,
            {
                "mode": "update-db",
                "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
                "files_downloaded": 0,
                "files_processed": 0,
                "validation_status": "ERROR",
                "latest_available_period": "N/A",
                "database_status": "promotion_blocked",
                "automation_mode": "Manual run only",
                "message": "Validation errors found. Existing demo database remains unchanged.",
            },
        )
        return False

    if not config.candidate_db_path.exists():
        append_event(config, "promote_db", "ERROR", "Candidate DuckDB does not exist.")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = config.backup_dir / f"insurance_market_{timestamp}.duckdb"
    shutil.copy2(config.current_db_path, backup_path)
    shutil.copy2(config.candidate_db_path, config.current_db_path)
    append_event(config, "promote_db", "PASS", f"Promoted candidate database. Backup: {backup_path}")
    write_status(
        config,
        {
            "mode": "update-db",
            "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
            "files_downloaded": 0,
            "files_processed": 0,
            "validation_status": "PASS" if (report["result"] == "PASS").all() else "WARNING",
            "latest_available_period": "N/A",
            "database_status": "promoted",
            "automation_mode": "Manual run only",
            "message": "Candidate DuckDB promoted after validation. A timestamped backup was created.",
        },
    )
    return True


def update_duckdb(config: PipelineConfig, promote: bool = False) -> bool:
    if not build_candidate_database(config):
        return False
    if promote:
        return promote_candidate_database(config)

    report, has_errors = validate_pipeline_outputs(config, mode="update-db")
    validation_status = "ERROR" if has_errors else ("WARNING" if (report["result"] == "WARNING").any() else "PASS")
    write_status(
        config,
        {
            "mode": "update-db",
            "discovery_status": "available" if config.discovered_sources_path.exists() else "not_run",
            "files_downloaded": 0,
            "files_processed": 0,
            "validation_status": validation_status,
            "latest_available_period": "N/A",
            "database_status": "candidate_built_not_promoted",
            "automation_mode": "Manual run only",
            "message": "Candidate DuckDB was built. Current demo database remains unchanged until --promote is used after review.",
        },
    )
    return True
