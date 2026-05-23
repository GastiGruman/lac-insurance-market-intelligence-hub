# News Module

## Purpose

The News / External Intelligence module gives treaty brokers a controlled place to review manually curated public context around a selected company.

It is designed to support meeting preparation, not automated media monitoring or formal due diligence.

## Current Mode: Curated / Manual

Phase 4D uses curated/manual mode only.

The app reads:

- `data/external/company_news_curated.csv`
- `data/external/company_key_people_template.csv`

These files are small, committed templates. They do not contain scraped dumps, confidential information, secrets, or raw provider output.

If no rows are available for a selected company, the app shows:

`No curated news available for the selected company yet.`

## Curated News File Fields

Expected columns:

- `company_name`
- `company_name_norm`
- `country`
- `title`
- `date`
- `source`
- `url`
- `summary`
- `broker_relevance`
- `relevance_category`
- `relevance_score`
- `is_verified`
- `notes`

Each row should represent one manually reviewed public item. Source, date and link should be clear enough for a broker or reviewer to validate before use.

## Broker Relevance Categories

Supported categories:

- Strategy
- Financial Results
- Regulation
- Claims / Catastrophe
- Product / Distribution
- M&A / Partnerships
- Technology / AI
- Leadership
- Reinsurance / Capital
- Other

## Key People / Leadership

Phase 4D does not search for or invent key people.

The template file is:

`data/external/company_key_people_template.csv`

Expected columns:

- `company_name`
- `role`
- `person_name`
- `source`
- `source_url`
- `last_verified_date`
- `notes`

Only manually verified and appropriate names should be added in the future.

## Future Live Mode

Live news retrieval is disabled by default. Future implementation may use approved API-based providers only, with caching, source metadata, and governance controls.

Uncontrolled scraping is not part of the design.

## AI Brief Integration

The app builds a structured `company_news_context` containing:

- selected company and filters,
- curated news items,
- recent topics,
- broker relevance summary,
- suggested questions,
- limitations.

Future AI Brief versions can consume this context, but Phase 4D does not call an external LLM.

## Methodology / Trust Note

External intelligence is not the same as Fasecolda structured market data. News items should be treated as contextual information, with source/date/link validation required before formal use.

## Limitations

- Current version is not a live news feed.
- Empty curated files are valid and should show friendly fallbacks.
- News relevance is rule-based and manually supplied.
- News should be validated against the original public source before use in client or market presentations.
- No paid APIs or secrets are required for the app to run.
