from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelineConfig:
    project_root: Path
    country: str = "COLOMBIA"
    regulator: str = "FASECOLDA"
    region: str = "LATIN AMERICA AND CARIBBEAN"
    currency: str = "COP"

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw" / "fasecolda"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed" / "fasecolda"

    @property
    def database_dir(self) -> Path:
        return self.data_dir / "database"

    @property
    def metadata_dir(self) -> Path:
        return self.data_dir / "metadata"

    @property
    def mapping_dir(self) -> Path:
        return self.data_dir / "mappings"

    @property
    def current_db_path(self) -> Path:
        return self.database_dir / "insurance_market.duckdb"

    @property
    def candidate_db_path(self) -> Path:
        return self.database_dir / "insurance_market_candidate.duckdb"

    @property
    def backup_dir(self) -> Path:
        return self.database_dir / "backups"

    @property
    def discovered_sources_path(self) -> Path:
        return self.metadata_dir / "discovered_sources.csv"

    @property
    def source_manifest_path(self) -> Path:
        return self.metadata_dir / "source_manifest.csv"

    @property
    def validation_report_path(self) -> Path:
        return self.metadata_dir / "pipeline_validation_report.csv"

    @property
    def latest_status_json_path(self) -> Path:
        return self.metadata_dir / "latest_pipeline_status.json"

    @property
    def latest_status_md_path(self) -> Path:
        return self.metadata_dir / "latest_pipeline_status.md"

    @property
    def company_mapping_path(self) -> Path:
        return self.mapping_dir / "company_mapping.csv"

    @property
    def lob_mapping_path(self) -> Path:
        return self.mapping_dir / "line_of_business_mapping.csv"


def get_config() -> PipelineConfig:
    return PipelineConfig(project_root=Path(__file__).resolve().parents[2])


def ensure_pipeline_dirs(config: PipelineConfig) -> None:
    for path in [
        config.raw_dir,
        config.processed_dir,
        config.database_dir,
        config.metadata_dir,
        config.backup_dir,
    ]:
        path.mkdir(parents=True, exist_ok=True)

