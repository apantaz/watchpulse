# AGENTS.md

## Project Goal

Design the architecture for a production-minded data product that helps users discover the best new streaming releases available in their country across the streaming services they subscribe to.

The initial market is Greece, but the architecture must be designed so that additional countries can be supported later without major redesign.

The core user problem is:

> "I live in Greece, I subscribe to Netflix, Disney+, Prime Video, etc. What are the best new releases available to me this week, and what is actually worth watching?"

This is not intended to be a generic movie/TV catalog or a JustWatch clone. The product should focus on curated discovery of newly available or newly released content.

---

## Product Principles

1. New releases first.
2. Country-aware availability.
3. Provider-aware recommendations.
4. Simple discovery instead of overwhelming catalog browsing.
5. Explain why something is recommended.
6. Preserve historical availability and ranking data rather than only current state.
7. Start small, but design the architecture so it can evolve into a real public product.

---

## Initial User Experience

A user should eventually be able to select:

- Country
- Streaming providers they subscribe to
- Optional content preferences

Example:

- Country: Greece
- Netflix
- Disney+
- Prime Video

The main experience should answer questions such as:

- What are the top releases this week?
- What is a must-watch?
- What is trending?
- What are the best new movies?
- What are the best new TV series?
- What new episodes or seasons appeared?
- What hidden gems were added?
- What was newly added to my providers?
- What content has recently become available in my country?

Future extensions may include:

- Personalized recommendations
- Watchlists
- User viewing history
- "I have 2 hours, what should I watch?"
- Genre exclusions/preferences
- Alerts/digests
- Leaving-soon content
- Historical provider availability

Do not design all future features now, but do not create an architecture that blocks them.

---

## Primary Data Source

TMDB should be treated as the initial external metadata source.

Relevant types of data may include:

- Movies
- TV shows
- Seasons
- Episodes
- Genres
- People
- Images
- Popularity
- Vote averages
- Vote counts
- Release dates
- Content metadata
- Watch providers
- Country/region-specific availability

The architecture must account for the fact that external APIs represent current state and may not provide complete historical state.

We want to retain our own historical snapshots where useful.

Do not assume TMDB is the only source forever.

Design source abstraction so additional sources can be added later, such as:

- IMDb-derived datasets where legally appropriate
- Rotten Tomatoes or critic sources where API/licensing permits
- JustWatch-compatible/provider availability sources
- Streaming-platform-specific feeds
- Editorial/manual curation
- Other public entertainment datasets

Do not introduce paid dependencies unless there is a strong reason.

---

## Important Domain Concepts

The architecture should clearly separate these concepts.

### Title

A movie or TV show.

Potential future extension:

- season
- episode

### Provider

Examples:

- Netflix
- Disney+
- Prime Video
- Apple TV+

### Country / Market

Examples:

- GR
- GB
- DE
- US

Availability must be country-aware.

### Streaming Availability

A relationship between:

- title
- provider
- country
- availability type
- observed time

We want to be able to identify when availability changes.

Potential availability types:

- subscription
- free
- ads
- rent
- buy

The main product should initially prioritize subscription streaming.

### Release

A content release event.

Do not assume a single global `release_date` is sufficient.

Different release concepts may exist:

- original premiere
- theatrical release
- digital release
- streaming availability
- season release
- episode air date

The architecture should define what the product means by "new this week."

### Ranking / Recommendation

The product should calculate its own ranking rather than simply sorting by TMDB rating.

Potential signals:

- rating quality
- vote count
- popularity
- recency
- popularity momentum
- genre
- provider
- country
- release freshness
- editorial signals
- user preferences later

The ranking should be explainable.

Example output:

- Must Watch
- Worth Watching
- Trending
- Hidden Gem

Do not implement an opaque ML system for the first version.

---

## Data Engineering Requirements

The architecture should demonstrate serious data engineering and analytics engineering practices.

Consider:

- API ingestion
- incremental ingestion
- idempotency
- retries
- rate limits
- schema evolution
- raw data preservation
- history tracking
- snapshots
- deduplication
- source freshness
- data quality checks
- orchestration
- observability
- lineage
- reproducibility
- local development
- production deployment

Avoid unnecessary enterprise complexity.

The initial system should be able to run cheaply or for free.

---

## Analytics Engineering Requirements

The transformed data layer should have clearly defined grains.

Possible entities/models to consider:

- dim_title
- dim_movie
- dim_tv_show
- dim_provider
- dim_country
- dim_genre
- dim_person

- fct_streaming_availability
- fct_release
- fct_title_daily_metrics
- fct_ranking
- fct_provider_catalog_snapshot

Potential marts:

- mart_weekly_releases
- mart_must_watch
- mart_trending
- mart_hidden_gems
- mart_provider_weekly_summary

These names are suggestions, not requirements.

The agent should determine the correct modeling strategy.

For every proposed fact table, document:

- Grain
- Primary key
- Important dimensions
- Measures
- Update strategy
- Historical behavior

---

## History Requirement

Historical tracking is important.

Examples of questions the future system should be able to answer:

- When did title X first become available on Netflix Greece?
- Was title X removed and later re-added?
- How long was it available?
- Which titles were added this week?
- Which provider added the most highly rated content this month?
- How did a title's popularity evolve after release?
- What was ranked #1 last Friday?

Do not overwrite all previous states.

The architecture should explicitly define which data is:

- append-only
- snapshot-based
- slowly changing
- current-state only

---

## Recommended Technology Philosophy

Prefer open-source and low-cost tools.

The architecture should evaluate, rather than blindly adopt, technologies such as:

- Python
- DuckDB
- PostgreSQL
- dbt
- dbt-duckdb or dbt-postgres
- Parquet
- object storage
- GitHub Actions
- lightweight orchestration
- FastAPI
- Streamlit
- Next.js or another frontend
- Docker

Do not assume Snowflake, BigQuery, Databricks, Airflow, Kafka, Kubernetes, or paid SaaS are required.

If recommending heavier infrastructure, explain exactly why.

The initial project should be realistic for one developer.

---

## Architecture Constraints

The first version should:

- Be runnable locally.
- Be deployable cheaply.
- Support Greece first.
- Support multiple streaming providers.
- Preserve useful historical data.
- Support daily ingestion.
- Support weekly rankings.
- Have a clean analytical model.
- Allow a future public API/frontend.
- Avoid vendor lock-in where practical.

The architecture must support scaling to more countries later.

Do not prematurely optimize for millions of users.

---

## MVP Scope

The first usable version should focus on:

1. Greece.
2. Movies and TV shows.
3. A small number of major providers.
4. Daily ingestion.
5. Historical availability tracking.
6. Weekly release identification.
7. Basic deterministic ranking.
8. A simple consumption layer.

Example MVP output:

> Greece — This Week

- Top 5 Must-Watch Releases
- New on Netflix
- New on Disney+
- New on Prime Video
- Trending
- Hidden Gems

Do not include authentication, social features, complex personalization, payments, or machine learning in the MVP architecture unless there is a compelling architectural dependency.

---

## Ranking Requirements

Design a ranking framework, but do not over-engineer it.

A first version could use signals such as:

- normalized rating
- vote confidence
- popularity
- popularity change
- recency
- release relevance
- genre weighting

The system should avoid obvious ranking failures such as:

- 10.0 rating from 3 votes beating 8.2 from 20,000 votes
- old catalog titles dominating "new this week"
- duplicated movie/provider entries
- rental availability appearing as subscription availability

The ranking logic should be stored and versioned in the analytics layer where possible.

---

## Data Quality

The proposed architecture should include tests for cases such as:

- duplicate titles
- duplicate provider availability
- missing provider IDs
- invalid country codes
- impossible dates
- availability records without a title
- unknown monetization types
- unexpected drops in ingested titles
- stale ingestion
- null critical identifiers
- ranking output containing unavailable content

Tests should be divided into:

- source checks
- transformation checks
- business-rule checks

---

## Repository Design

Propose a clean repository structure.

The repository may eventually contain:

- ingestion code
- dbt project
- API
- frontend
- infrastructure
- tests
- documentation

Do not create the full implementation yet.

First produce a repository architecture and explain ownership/boundaries between components.

---

## Documentation Expectations

The architecture should produce clear documentation for:

- system context
- components
- data flow
- storage
- ingestion
- transformations
- serving
- deployment
- observability
- security
- failure handling
- data contracts
- scaling path

Use Mermaid diagrams where useful.

---

## Agent Task

Your first task is architecture only.

Do not immediately generate the application.

Do not create dozens of implementation files.

Instead:

1. Analyze the product requirements in this document.
2. Identify ambiguous domain decisions.
3. Make reasonable assumptions and document them.
4. Propose 2-3 viable architecture options.
5. Compare their trade-offs.
6. Recommend one architecture for the MVP.
7. Design the end-to-end data flow.
8. Define storage choices.
9. Define ingestion strategy.
10. Define historical tracking strategy.
11. Propose the analytical data model.
12. Define orchestration.
13. Define serving/API strategy.
14. Define frontend boundaries.
15. Define deployment strategy.
16. Define testing and observability.
17. Define how the architecture can evolve from Greece-only to multi-country.
18. Propose a repository structure.
19. Produce Mermaid architecture and data-model diagrams.
20. Write the final proposal into:

`docs/architecture.md`

Do not implement the project until the architecture has been reviewed.

---

## Architecture Decision Priorities

When making trade-offs, optimize in this order:

1. Correct data model
2. Useful product
3. Maintainability
4. Low operational cost
5. Developer simplicity
6. Data history
7. Extensibility
8. Performance
9. Scale

Do not choose a complex technology simply because it looks impressive in a portfolio.

The architecture should look like something a strong Data/Analytics Engineer would genuinely choose for this workload.

---

## Final Architecture Deliverable

`docs/architecture.md` should contain at minimum:

- Problem statement
- Product scope
- Assumptions
- Non-goals
- Domain model
- Architecture options considered
- Recommended architecture
- System diagram
- Data flow
- Storage model
- Ingestion design
- Transformation/dbt design
- Historical tracking
- Ranking design
- Serving/API layer
- Frontend boundary
- Testing
- Observability
- Failure recovery
- Deployment
- Cost considerations
- Security considerations
- Scaling strategy
- Repository structure
- MVP implementation phases
- Open questions

End the document with a short section:

## Decisions Needed Before Implementation

Only after those decisions are reviewed should implementation begin.
