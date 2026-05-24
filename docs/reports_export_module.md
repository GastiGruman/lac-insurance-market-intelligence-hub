# Reports / Export Module

## Purpose

The Reports / Export module gives brokers practical outputs for meetings, emails, internal notes and slide preparation.

It is intentionally lightweight. Phase 4E prioritizes copy-ready markdown, CSV and in-memory Excel over complex PDF or PowerPoint generation.

## Export Types

### Company Brief

Copy-ready markdown with:

- Executive summary.
- Executive snapshot.
- Market position.
- Main competitors.
- Portfolio mix.
- Key technical signals.
- Reinsurance preview.
- Suggested broker questions.
- Methodology footer.

### AI Brief

Copy-ready markdown generated from the internal-data AI Brief context. It does not call an external AI API.

Includes:

- Executive summary.
- Market / company context.
- Portfolio focus.
- Reinsurance angles.
- Suggested questions.
- Validation notes.

### Reinsurance Summary

Treaty-broker-ready markdown with:

- Emitted premium.
- Retained premium.
- Ceded premium.
- Cession ratio.
- Retention ratio.
- Company vs market benchmark where available.
- Key lines by ceded premium.
- Treaty discussion signals.
- Suggested questions.

### Market Summary

Market-level markdown with:

- Total premium.
- Claims / Premiums.
- Top companies.
- Top lines of business.
- Methodology notes.

### Broker One-Pager

Compact copy-ready markdown for quick meeting preparation:

- Executive Snapshot.
- What changed?
- What matters for a broker?
- Reinsurance discussion angles.
- Suggested questions.
- Data / methodology notes.

### PPT-Ready Bullets

Short markdown bullets designed to be copied into slides. No actual PowerPoint file is generated in Phase 4E.

### Filtered Data

Downloads the current filtered app data:

- CSV export.
- Excel export when the runtime supports `openpyxl`.

Exports are generated in memory. The app does not write export files to tracked folders.

## Export Metadata

Every markdown export includes:

- Generated from LAC Insurance Market Intelligence Hub.
- Country.
- Company.
- Line of business.
- Years.
- Data source.
- Generated date/time.
- Methodology note.

## Methodology Notes

Exports include these guardrails:

- Claims / Premiums is analytical and not necessarily official technical siniestralidad or combined ratio.
- Reinsurance indicators are exploratory where source limitations apply.
- External intelligence is curated/manual and may be empty.
- Outputs should be validated before formal client or market presentations.

## Current Limitations

- PDF generation is not implemented.
- Actual PowerPoint file generation is not implemented.
- Excel export depends on installed runtime support.
- Exports reflect the current static demo database and selected app filters.

## Future Enhancements

- Branded PDF export after design and dependency review.
- Actual PowerPoint export after template governance.
- Export bundles that combine brief, charts and filtered tables.
- Controlled integration of curated external intelligence into selected report types.
