# Mapping Methodology

## Why Mapping Is Needed

Fasecolda sources do not always use identical company or line-of-business names. A broker-facing market intelligence tool needs consistent labels so users can compare companies, lines, and reinsurance indicators without manually translating source names.

The app uses mapping tables as an analytical standardization layer. They do not replace legal entity review or formal regulatory classification.

## Company Mapping

Company mapping is stored in:

- `data/mappings/company_mapping.csv`
- `data/mappings/company_mapping_normalized.csv`
- DuckDB table `dim_company_mapping`

Typical fields include:

- `country`
- `source`
- `source_company`
- `standard_company`
- `group_name`
- `company_type`

The app uses `standard_company` for filters, rankings, charts, briefs, and exports. When a source uses a different name for the same insurer, the mapping table connects it to the standard name.

## Line-of-Business Mapping

Line-of-business mapping is stored in:

- `data/mappings/line_of_business_mapping.csv`
- `data/mappings/line_of_business_mapping_normalized.csv`
- DuckDB table `dim_line_of_business_mapping`

Typical fields include:

- `country`
- `source`
- `source_line_of_business`
- `standard_line_of_business`
- `lob_group`

The app uses `standard_line_of_business` for filters, rankings, charts, briefs, and exports.

## Normalized Names

Normalized names are comparison keys used to improve matching. They may remove accents, trim spaces, and standardize uppercase text. They are useful for matching but should not be treated as user-facing labels.

## Standard Names

Standard names are the app's preferred analytical labels. They are designed to make market views consistent across modules and, eventually, across countries.

## LOB Groups and Aggregate Lines

`lob_group` helps identify lines that should be handled carefully. In particular:

- `AGGREGATE` lines can duplicate individual lines.
- Reinsurance View excludes aggregate lines from rankings by default.
- Users can include aggregates when they want to inspect the source structure, but results should be treated cautiously.

Examples of aggregate lines include total damages, total persons, and total social security categories.

## Limitations

- Some company groups may include multiple legal entities.
- Naming may change over time.
- A mapping can be analytically useful while still requiring broker review.
- Missing mappings should result in "data not available" behavior, not invented equivalences.
- Mapping updates should be documented and reviewed when new sources are added.
