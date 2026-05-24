# Roadmap - LAC Insurance Market Intelligence Hub

## Phase 1 - Colombia MVP Stability

Status: completed.

Focus:

- Stable Streamlit Cloud demo.
- Defensive filters.
- Lazy navigation.
- Friendly warnings instead of app crashes.
- Demo branch with DuckDB snapshot.

## Phase 2 - Colombia Methodology and Trust Layer

Status: completed in this branch.

Focus:

- Data dictionary.
- Methodology notes.
- Source-to-module traceability.
- Mapping methodology.
- Validation notes.
- Improved Data Status transparency.

## Phase 3 - Automatic Fasecolda Data Ingestion Pipeline

Status: in progress in this branch.

Focus:

- Download or retrieve public Fasecolda files.
- Detect new periods.
- Normalize and validate files.
- Update DuckDB safely.
- Produce logs and validation reports.
- Prevent bad loads from replacing trusted data.

Initial implementation:

- Official Fasecolda landing pages configured.
- Manual source registry fallback.
- Download manifest.
- Normalized processed outputs.
- Mapping integration and unmapped review files.
- Pipeline validation reports.
- Candidate DuckDB strategy with explicit promotion flag.

### Phase 3B - Candidate Database Review

Status: in progress in this branch.

Focus:

- Compare current and candidate DuckDB files.
- Generate local reconciliation outputs.
- Test app compatibility against candidate mode.
- Document promotion recommendation.
- Block promotion if the candidate only adds audit tables or does not materially refresh app-facing tables.

## Phase 4 - Broker-Focused Refinements

Status: in progress.

Focus:

- Internal user feedback.
- Meeting-prep workflows.
- Cleaner reports.
- Better signal thresholds.
- More explicit caveats where needed.
- Separate official technical indicator views from analytical Claims / Premiums ratios where Fasecolda methodology is available.
- Show both the app's Claims / Premiums ratio and official technical indicators or combined ratios when source methodology has been confirmed.

### Phase 4A - Advanced Company Brief

Status: implemented in this branch.

Focus:

- Convert Company Brief into a broker-ready executive intelligence page.
- Add market position, competitors, portfolio mix, growth signals, technical alerts and meeting questions.
- Keep the brief grounded in structured DuckDB/Fasecolda data.
- Leave external intelligence, key people and news to later AI Brief / News phases.

### Phase 4B - Advanced Reinsurance View

Status: implemented in this branch.

Focus:

- Convert Reinsurance View into a treaty-broker preparation page.
- Add executive reinsurance snapshot, company vs market benchmark, reinsurance by line, evolution, treaty signals and broker questions.
- Keep reinsurance indicators grounded in Fasecolda - Indicadores de Gestion 2025 and mapping tables.
- Preserve the exploratory methodology warning until the source is fully validated for production use.
- Leave AI-generated interpretation to a later controlled AI phase.

### Phase 4C - Internal-Data AI Brief

Status: implemented in this branch.

Focus:

- Generate a broker-ready AI-style brief from internal structured data.
- Reuse Company Brief, Reinsurance View, technical signals, market context and methodology limitations.
- Provide constrained question routing for reinsurance, competitors, portfolio lines, meeting questions and validation notes.
- Keep the module deterministic and functional without external API keys.
- Leave external AI, news, key people, ratings and financial statements to later governed phases.

### Phase 4D - Curated Company News / External Intelligence

Status: implemented in this branch.

Focus:

- Add a controlled external intelligence layer using curated/manual files.
- Display news source, date, link, category, verification flag and broker relevance.
- Generate rule-based broker interpretation and suggested questions.
- Add key people / leadership template without inventing names.
- Keep live news retrieval disabled by default and reserve it for future approved providers.

### Phase 4E - Broker Reports / Export Center

Status: implemented in this branch.

Focus:

- Add practical copy-ready exports for broker workflows.
- Support Company Brief, AI Brief, Reinsurance Summary, Market Summary, Broker One-Pager and PPT-ready bullets.
- Add filtered CSV and optional in-memory Excel export.
- Include methodology footers in markdown exports.
- Leave PDF and actual PowerPoint generation to future dependency and template review.

### Phase 4F - Operational Maintenance Readiness

Status: implemented in this branch.

Focus:

- Document the controlled maintenance workflow for manual Fasecolda updates.
- Add release and smoke-test checklists.
- Document future scheduling options without activating a scheduler.
- Clarify database promotion rules and rollback approach.
- Provide a read-only maintenance check for required paths, database presence and Git ignore protections.
- Prepare the project for IT/Data handoff while keeping the Streamlit Cloud demo stable.

Scheduled automation remains planned, not live.

## Phase 5 - Internal Presentation Readiness And Governed Intelligence

Status: in progress.

### Phase 5A - UX / Visual Polish For Internal v1

Status: implemented in this branch.

Focus:

- Make the app feel like a polished internal broker intelligence product.
- Improve the top header, sidebar wording, module headers and empty states.
- Keep labels consistent, especially Claims / Premiums versus official technical indicators.
- Improve Data Status readability and Reports / Export usability.
- Preserve all existing functionality, calculations and database behavior.

### Phase 5B - Controlled External AI Module

Status: planned.

Focus:

- Use only structured data and approved sources.
- No invented facts.
- Clear source and period citations.
- Broker meeting preparation support.

## Phase 6 - Live Company News Module

Status: planned.

Focus:

- Approved API-based company and market news.
- Regulatory and rating-action monitoring where available.
- Broker relevance summaries.
- Verification warnings before client use.

## Phase 7 - Regional Expansion

Status: future.

Potential countries:

- Colombia.
- Mexico.
- Chile.
- Peru.
- Argentina.
- Costa Rica.
- Panama.
- Ecuador.
- Dominican Republic.

Regional expansion will require country-by-country source review, mapping methodology, currency treatment, and regulatory context.
