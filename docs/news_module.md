# News Module

## Purpose

The News module adds optional source-based company and market news for broker meeting preparation.

It is designed to support:

- Recent company news.
- Regulatory news.
- Rating-action monitoring when returned by the configured provider.
- Corporate press releases when returned by the configured provider.
- Market-relevant insurance, macro, regulatory and AI/technology signals.

## Sources Supported

The module is optional and provider-based.

Supported environment variables:

- `NEWS_API_KEY`
- `BING_SEARCH_API_KEY`
- `SERPAPI_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_ENGINE_ID` for Google Custom Search

If no provider is configured, the app shows:

`News module not configured.`

## Configuration

Set provider keys as environment variables. Do not hardcode API keys in the repository.

Example provider options:

- NewsAPI for general news search.
- Bing Search for news search.
- SerpAPI with Google News engine.
- Google Custom Search with a configured search engine ID.

## Update Frequency And Caching

The module uses Streamlit controls plus local JSON cache files under:

`outputs/news_cache/`

Default local cache TTL:

- 12 hours.

The app includes a refresh button to request fresh provider results.

## How News Is Displayed

Each news item shows:

- Title.
- Source.
- Date.
- Link.
- Short summary.
- Broker relevance.

Broker relevance is rule-based and flags possible themes such as:

- Reinsurance angle.
- Regulatory monitoring.
- Rating or credit watch.
- Market performance context.
- AI or technology signal.

## AI Summaries

If AI is configured, the app can summarize retrieved news items.

AI summaries include:

- What happened.
- Why it matters.
- Possible reinsurance relevance.
- Suggested question for client meeting.
- Sources used.

The AI prompt receives only the retrieved news item title, source, date, link, summary and relevance. It must cite source and date and must not invent facts.

## Limitations

- The module does not scrape aggressively.
- Search results depend on the configured provider.
- Dates may be unavailable for some providers.
- Search APIs may return partial, duplicated or irrelevant results.
- News should be verified against the original source before client use.
- AI summaries are optional and should be reviewed before use in meetings.
