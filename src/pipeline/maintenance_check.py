from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = [
    "app",
    "src",
    "src/pipeline",
    "docs",
    "data",
    "data/database",
    "data/mappings",
    "app/streamlit_app.py",
    "data/database/insurance_market.duckdb",
    "data/mappings/company_mapping.csv",
    "data/mappings/line_of_business_mapping.csv",
]


GITIGNORE_REQUIRED_PATTERNS = [
    ".venv/",
    "__pycache__/",
    "*.pyc",
    ".env",
    ".streamlit/secrets.toml",
    "data/raw/",
    "data/processed/",
    "data/metadata/**",
    "data/database/backups/",
    "data/database/*candidate*.duckdb",
    "outputs/",
    "*.log",
]


def _status(ok: bool) -> str:
    return "PASS" if ok else "ERROR"


def _check_paths() -> list[tuple[str, str, str]]:
    results = []
    for relative_path in REQUIRED_PATHS:
        path = PROJECT_ROOT / relative_path
        results.append(("Required path", relative_path, _status(path.exists())))
    return results


def _check_gitignore() -> list[tuple[str, str, str]]:
    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return [(".gitignore", ".gitignore file", "ERROR")]

    content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    results = []
    for pattern in GITIGNORE_REQUIRED_PATTERNS:
        results.append((".gitignore pattern", pattern, _status(pattern in content)))
    return results


def _check_candidate_database() -> list[tuple[str, str, str]]:
    candidate_path = PROJECT_ROOT / "data/database/insurance_market_candidate.duckdb"
    status = "WARNING" if candidate_path.exists() else "PASS"
    detail = "candidate exists; review before promotion" if candidate_path.exists() else "no candidate present"
    return [("Candidate database", detail, status)]


def main() -> int:
    print("LAC Insurance Market Intelligence Hub - Maintenance Check")
    print(f"Project root: {PROJECT_ROOT}")
    print()

    results = []
    results.extend(_check_paths())
    results.extend(_check_gitignore())
    results.extend(_check_candidate_database())

    for category, item, status in results:
        print(f"[{status}] {category}: {item}")

    has_error = any(status == "ERROR" for _, _, status in results)

    print()
    print("Recommended next commands:")
    print("  python -m src.pipeline.run_colombia_pipeline --mode discover")
    print("  python -m src.pipeline.run_colombia_pipeline --mode validate")
    print("  python -m src.pipeline.compare_candidate_database")
    print("  python -m streamlit run app\\streamlit_app.py")
    print()
    print("This check is read-only. It does not download, promote, delete, or write data files.")

    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())

