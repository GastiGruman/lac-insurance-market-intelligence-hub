# AI Module

## What It Does

The AI module adds an optional controlled AI layer for broker meeting preparation.

Current sections:

- AI Brief.
- Ask the Data.
- AI Meeting Prep.

The AI Brief and AI Meeting Prep use only structured context prepared by the app from DuckDB tables and calculated pandas summaries.

## Data Used

The AI context can include:

- Selected country.
- Selected company.
- Optional line of business.
- Selected years.
- Meeting purpose and meeting type.
- Premium evolution.
- Claims and Claims / Premiums ratio evolution.
- Market share.
- Main lines of business.
- Fastest growing lines.
- Lines with deteriorating Claims / Premiums ratio.
- Exploratory reinsurance summary when available.
- Source, period and methodology notes.

Primary source:

- Fasecolda - Ciudades y Ramos.

Complementary exploratory source:

- Fasecolda - Indicadores de Gestion 2025.

## What It Does Not Do

The module does not:

- Invent data.
- Run arbitrary SQL.
- Allow model-generated queries.
- Scrape news or external websites.
- Mention executives, private information, ratings or regulatory events unless those are present in approved source data.
- Provide legal, actuarial, investment or financial advice.

## Configuration

AI features are optional. If no provider is configured, the app shows:

`AI features are not configured yet.`

Supported environment variables:

### OpenAI

- `OPENAI_API_KEY`
- `OPENAI_MODEL` optional

### Azure OpenAI

- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION` optional

Do not hardcode API keys in the repository.

## Ask the Data

The first version of Ask the Data uses controlled templates and safe pandas calculations.

Supported examples:

- Companies with highest premium growth.
- Company versus market comparison.
- Lines or companies with highest exploratory cession ratio.
- Suggested meeting questions based on selected filters.

If a question is outside available data, the app returns a data-not-available message.

## Guardrails

AI prompts require the model to:

- Use only provided structured context.
- Mention source and period.
- Distinguish observed data from broker interpretation.
- Avoid comparing YTD with full-year periods without warning.
- Avoid legal or financial advice.
- Keep outputs concise and broker-focused.

## Limitations

- Indicadores de Gestion 2025 remains exploratory pending methodology review.
- Aggregate lines may duplicate individual lines.
- AI output should be reviewed before client use.
- The module does not yet include news or external-source retrieval.
