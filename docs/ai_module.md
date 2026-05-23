# AI Brief Module

## Current Status

Phase 4C implements an internal-data AI Brief. It does not require an external LLM, API key, internet access, news search, or web scraping.

The current module is deterministic and rule-based. It uses structured data already available in the app to produce a broker-ready intelligence brief for meeting preparation.

## Data Used

The AI Brief can use:

- Selected country, company, line of business and years.
- Market Overview context from Fasecolda - Ciudades y Ramos.
- Company Brief context, including market position, competitors, portfolio mix, alerts and broker questions.
- Reinsurance View context from Fasecolda - Indicadores de Gestion 2025 where mapped.
- Technical signals generated from internal structured data.
- Methodology and data-status limitations.

## What It Produces

The deterministic brief includes:

- Executive summary.
- Market position.
- Portfolio and line-of-business focus.
- Performance and technical signals.
- Reinsurance discussion angles.
- Broker talking points.
- Suggested meeting questions.
- Methodology and data limitations.
- Next steps for broker preparation.

It also includes a constrained internal-data question box. The first version routes questions to available internal contexts such as reinsurance, competitors, portfolio lines, meeting questions and validation notes.

## Brief Types

The app supports these use cases:

- Pre-meeting company brief.
- Reinsurance discussion brief.
- Portfolio review brief.
- Market comparison brief.
- Internal strategy brief.

The selected type changes the emphasis of the generated brief, but all output remains grounded in internal structured data.

## External Intelligence Not Yet Connected

The module does not currently include:

- Company news.
- Ratings or rating actions.
- Financial statements.
- Key people or leadership.
- Live web search.
- External LLM-generated interpretation.

These are planned future enhancements subject to source review, security configuration and governance.

## Guardrails

- Do not invent facts or numbers.
- Use only internal structured data from DuckDB, mapping tables and app calculations.
- Clearly distinguish observed data from broker interpretation.
- Treat Claims / Premiums as an analytical ratio, not official technical siniestralidad or combined ratio.
- Treat reinsurance indicators as exploratory where source limitations apply.
- Validate figures before formal client, market, actuarial or financial presentations.

## Optional Future LLM Configuration

The repository still contains optional AI provider configuration utilities for future controlled LLM use. No API key is required for Phase 4C.

Future provider variables may include:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`

Do not hardcode API keys in the repository.
