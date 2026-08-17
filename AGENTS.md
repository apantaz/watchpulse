# AGENTS.md — WatchPulse

## 1. Purpose

WatchPulse is a streaming discovery product.

Its core goal is to help a user answer:

> "What should I watch right now, on the streaming services I actually have, in my region?"

The product is **not** a TV guide and should not include linear TV schedules in the current scope.

The product should combine:

- streaming availability by region and provider,
- movie/TV metadata,
- dynamic filters,
- ranked discovery sections,
- and eventually natural-language discovery.

The first target is a clean, live, production-looking product that can be used as a real portfolio project and later evolved into a consumer product.

---

# 2. Core Product Idea

A user selects a region and one or more streaming services.

Example:

```text
Region: Greecea

Services:
Netflix
Disney+
Prime Video
```

The user can then dynamically refine the catalog using filters such as:

```text
Content type
Genre
Runtime
Release year
Rating
Language
```

All visible discovery sections must react to the same filters.

Initial sections:

```text
Top 10
New Releases
Recently Added
Upcoming
```

Later:

```text
Leaving Soon
New For You
Natural-language discovery
Personalized recommendations
```

Example natural-language query:

> "Δεν είμαι καλά, θέλω μια ταινιούλα να γελάσω σήμερα στο Netflix."

WatchPulse should interpret this as structured intent such as:

```json
{
  "provider": ["netflix"],
  "content_type": "movie",
  "mood": ["funny", "light", "uplifting"],
  "avoid": ["dark", "depressing"]
}
```

The LLM must **not** decide what is available on a provider.

The application's local catalog is the source of truth for availability.

---

# 3. Non-Negotiable Architecture Principle

External APIs are **ingestion sources**, not serving APIs.

User interactions must NEVER trigger external API calls.

Correct architecture:

```text
TMDB
        \
         \
          -> Scheduled ingestion -> Local data layer -> Backend/query layer -> Frontend
         /
Streaming Availability API
```

User interaction:

```text
User changes filters
        ↓
Backend builds a safe query
        ↓
Local serving dataset
        ↓
Results
```

Incorrect architecture:

```text
User changes filters
        ↓
TMDB request
        ↓
Streaming API request
        ↓
Results
```

Do not implement the incorrect architecture.

---

# 4. Technology Direction

Initial preferred stack:

```text
Python
DuckDB
dbt
Frontend framework of choice
GitHub Actions
```

The repository should remain simple and portable.

Avoid unnecessary infrastructure in the MVP.

Do not introduce:

```text
Kubernetes
Kafka
Spark
complex microservices
heavy distributed infrastructure
```

unless a real requirement appears later.

DuckDB is acceptable for the initial implementation and portfolio-scale serving.

Keep boundaries clean so the serving database can later be replaced without rewriting the entire application.

---

# 5. External Data Sources

## 5.1 TMDB

TMDB is the primary source for content identity and general metadata.

Use TMDB for:

```text
tmdb_id
title
original_title
content_type
overview
release_date
genres
runtime
original_language
poster_path
backdrop_path
cast
director / creators
TMDB rating
vote count
TMDB popularity
```

Use `tmdb_id` as the canonical external content identifier whenever possible.

TMDB may also be used for current provider/catalog discovery when useful.

Do not expose raw TMDB response structures directly to the frontend.

Transform TMDB data into internal models first.

---

## 5.2 Streaming Availability API

Use the Streaming Availability API for streaming lifecycle data.

Relevant concepts include:

```text
country / region
provider
availability type
availableSince
expiration information
new
removed
updated
expiring
upcoming
```

Use its changes endpoint where appropriate.

The application should ingest changes on a schedule and persist them.

Important:

The upstream API may expose only a limited historical window.

Therefore WatchPulse must maintain its own historical event table.

---

# 6. Region

Region is a first-class dimension.

The product must support multiple regions without redesigning the schema.

Use standardized country codes where possible.

Examples:

```text
GR
US
GB
DE
FR
IT
ES
```

Do not hardcode the application around Greece.

The user's selected region determines:

- which services are relevant,
- which titles are available,
- which titles are newly added,
- which titles are leaving,
- and which upcoming titles are relevant.

---

# 7. Streaming Providers

Users should be able to select one or multiple providers.

Example:

```text
Netflix       ✓
Disney+       ✓
Prime Video   ✓
Apple TV+     ○
Mubi          ○
```

The provider list should be region-aware.

Provider IDs from upstream APIs should be mapped into stable internal provider identifiers.

Do not let the frontend depend on an upstream provider ID that may change between sources.

Recommended internal shape:

```text
provider_key = netflix
provider_name = Netflix
```

---

# 8. Global Filters

All filters must operate locally against WatchPulse-owned data.

Initial global filters:

```text
region
provider
content_type
genre
runtime
release_year
minimum_rating
language
```

Possible future filters:

```text
cast
director
certification
keyword
original language
minimum vote count
mood
```

Example:

```text
Region: Greece

Providers:
Netflix
Disney+

Content type:
Movie

Genre:
Science Fiction

Runtime:
<= 120 minutes

Rating:
>= 7.0
```

Changing filters must only change the local query.

It must NOT trigger TMDB or Streaming Availability API calls.

---

# 9. Shared Filter Universe

All discovery sections must operate on the same active filtered universe.

Example active state:

```text
region = GR
providers = Netflix, Disney+
content_type = movie
genre = Science Fiction
runtime <= 120
rating >= 7
```

Then all sections should respect those constraints:

```text
Top 10
New Releases
Recently Added
Leaving Soon
Upcoming
New For You
```

Do not implement each section as an isolated product with separate filter behavior.

---

# 10. Top 10

Top 10 means WatchPulse's own ranking.

It does NOT mean the official Netflix Top 10.

Initial implementation may use TMDB popularity.

Conceptually:

```sql
SELECT *
FROM serving_catalog
WHERE <global_filters>
  AND is_available = TRUE
ORDER BY popularity_score DESC
LIMIT 10;
```

The ranking model must be replaceable later.

Possible future ranking inputs:

```text
TMDB popularity
TMDB rating
vote count
release recency
availability recency
user preference score
WatchPulse engagement
```

Do not tightly couple UI code to the exact ranking formula.

---

# 11. New Releases

New Releases means recently released content.

This is based on the movie/show release date, not the date it entered a streaming service.

Example:

```text
Movie release date: July 2026
Added to Netflix: August 2026
```

This title is a New Release because the content itself is new.

Initial configurable definition:

```text
release_date >= current_date - 90 days
```

Possible ranking:

```text
release recency
popularity
rating
vote count
```

Keep the threshold configurable.

---

# 12. Recently Added

Recently Added is different from New Releases.

Example:

```text
Titanic
Original release: 1997
Added to Netflix Greece: 2026-08-15
```

Then:

```text
Recently Added = YES
New Release = NO
```

Use:

```text
available_since
or upstream "new" events
```

Conceptually:

```sql
SELECT *
FROM serving_catalog
WHERE <global_filters>
  AND available_since >= current_date - INTERVAL '30 days'
ORDER BY available_since DESC;
```

Keep the recent window configurable.

---

# 13. Leaving Soon

Show content that is currently available but expected to leave soon.

Example:

```text
Blade Runner 2049
Netflix
Leaving in 5 days
```

Use expiration data / `expiring` events when available.

Conceptually:

```sql
WHERE is_available = TRUE
  AND expires_on BETWEEN current_date
                     AND current_date + INTERVAL '30 days'
ORDER BY expires_on ASC;
```

Keep the window configurable.

---

# 14. Upcoming

Show titles expected to arrive on a streaming platform soon.

Conceptually:

```sql
WHERE available_from > current_date
ORDER BY available_from ASC;
```

Use upstream `upcoming` events when available.

Upcoming titles may not yet be part of the currently available catalog.

Keep upcoming state distinct from currently available state.

---

# 15. New For You

This is a later-stage personalization feature.

The MVP does not require sophisticated machine learning.

Start with a deterministic score.

Potential signals:

```text
genre preference
provider preference
TMDB popularity
TMDB rating
vote count
release recency
availability recency
language preference
```

Conceptually:

```text
recommendation_score =
    genre_match_score
  + popularity_score
  + rating_score
  + preferred_provider_bonus
  + recency_bonus
```

The recommendation engine must be replaceable independently of the frontend.

Later versions may use:

```text
watched history
likes
dislikes
saved titles
clicks
semantic similarity
embeddings
collaborative filtering
```

---

# 16. Authentication and User Memory

Do NOT make login mandatory for basic discovery.

Initial product should work without an account.

Guest users can use:

```text
region
provider selection
filters
Top 10
New Releases
Recently Added
Upcoming
```

Guest preferences may be stored locally in the browser.

Example:

```json
{
  "region": "GR",
  "providers": ["netflix", "disney-plus"],
  "runtime_max": 120
}
```

Login can be introduced later for persistent personalization.

Logged-in features may include:

```text
watched
liked
disliked
saved
not interested
persistent preferences
cross-device profile
```

Core principle:

> No login required to discover.
> Login required to remember.

---

# 17. Natural-Language Discovery

Natural-language discovery is an important future differentiator.

Example:

> "Έχω 90 λεπτά και θέλω κάτι χαλαρό στο Netflix."

The system should extract intent and constraints.

Example:

```json
{
  "provider": ["netflix"],
  "runtime_max": 90,
  "mood": ["light", "relaxing"]
}
```

Then the application should query its own local serving dataset.

Correct flow:

```text
User prompt
    ↓
LLM intent parser
    ↓
structured filters / semantic preferences
    ↓
local query engine
    ↓
real available candidates
    ↓
ranking
    ↓
optional LLM explanation
```

Incorrect flow:

```text
User prompt
    ↓
LLM invents movie recommendations and availability
```

Do not implement the incorrect flow.

---

# 18. LLM Cost and Abuse Controls

The AI feature must be bounded.

Do NOT implement an unrestricted general-purpose chatbot.

Treat AI as a natural-language query interface.

Recommended controls:

```text
max prompt length
per-session rate limit
per-user rate limit
per-IP rate limit where practical
daily global request cap
daily spend cap
usage logging
kill switch
```

Guests may have stricter limits than authenticated users.

Example conceptual limits:

```text
Guest:
5-10 AI searches/day

Logged-in:
20-30 AI searches/day
```

Keep actual values configurable.

Do not expose LLM API keys to the browser.

All LLM calls must go through the backend.

---

# 19. LLM Usage Monitoring

Track every AI request.

Recommended model:

```text
llm_usage

request_id
anonymous_session_id
user_id
model
input_tokens
output_tokens
estimated_cost
intent
status
created_at
```

Important metrics:

```text
AI requests today
AI requests this month
input tokens
output tokens
daily cost
monthly cost
cost per AI search
cost per active user
rate-limited requests
unsupported intents
errors
```

Implement a global kill switch so AI can be disabled while the rest of WatchPulse continues to work.

The product must remain useful without AI.

---

# 20. Unsupported AI Requests

If a user asks something unrelated to streaming discovery, WatchPulse should not become a general chatbot.

Example:

```text
"What is the capital of France?"
```

Return an application-level unsupported intent.

Example:

```json
{
  "intent": "unsupported"
}
```

UI can respond with a short message such as:

> I can help you find something to watch.

Do not spend multiple LLM turns having unrelated conversations.

---

# 21. Suggested Data Model

Exact schemas can evolve.

Keep raw/staging, normalized, and serving layers conceptually separate.

---

## 21.1 dim_content

```text
tmdb_id
content_type
title
original_title
overview
release_date
runtime_minutes
original_language
tmdb_rating
vote_count
tmdb_popularity
poster_path
backdrop_path
created_at
updated_at
```

---

## 21.2 content_genres

```text
tmdb_id
genre_id
genre_name
```

---

## 21.3 dim_provider

```text
provider_key
provider_name
source_provider_id
source_name
```

If multiple upstream sources are eventually used, prefer a proper mapping model rather than one overloaded source ID column.

---

## 21.4 streaming_availability

```text
tmdb_id
region
provider_key
monetization_type
available_since
expires_on
is_available
source
last_updated_at
```

Recommended natural grain:

```text
one row per
tmdb_id
+ region
+ provider
+ monetization type
```

unless the source requires a more detailed grain.

---

## 21.5 streaming_events

```text
event_id
tmdb_id
region
provider_key
event_type
event_date
source
ingested_at
```

Possible event types:

```text
new
removed
updated
expiring
upcoming
```

Do not delete historical events simply because the upstream API no longer returns them.

---

# 22. Serving Layer

The frontend should query application-owned serving models.

A possible serving model:

```text
catalog_availability
```

Possible fields:

```text
tmdb_id
title
content_type

region
provider_key
provider_name

release_date
runtime_minutes
original_language
genres

tmdb_rating
vote_count
popularity_score

available_since
expires_on

is_available
is_upcoming

poster_path
backdrop_path
```

Do not make the frontend understand raw TMDB or streaming-provider payloads.

---

# 23. Query Layer

Filters should be converted into controlled backend queries.

Example request:

```text
Region: GR
Provider: Netflix
Content type: movie
Genre: Thriller
Runtime <= 100
Rating >= 7
```

Conceptually:

```sql
SELECT *
FROM catalog_availability
WHERE region = ?
  AND provider_key = ?
  AND content_type = ?
  AND runtime_minutes <= ?
  AND tmdb_rating >= ?
  AND genre = ?
  AND is_available = TRUE
ORDER BY popularity_score DESC
LIMIT 10;
```

Use safe, parameterized queries.

Do not build raw SQL by concatenating untrusted user input.

---

# 24. Daily Ingestion Strategy

External APIs should be called on a schedule.

Initial target:

```text
Streaming availability refresh:
once per day

Streaming changes ingestion:
once per day

TMDB metadata enrichment:
incremental / as needed
```

Avoid repeatedly fetching metadata that is already current.

Use incremental ingestion whenever practical.

---

# 25. Historical Availability

WatchPulse should gradually build its own history.

Example:

```text
tmdb_id = 597
region = GR
provider = netflix
event_type = new
event_date = 2026-08-15
```

Later:

```text
tmdb_id = 597
region = GR
provider = netflix
event_type = removed
event_date = 2027-03-12
```

The local event history should outlive upstream historical windows.

This data can later power:

```text
Recently Added
historical availability
provider churn
catalog analysis
recommendation signals
```

---

# 26. API Cost Principle

External API usage should scale mainly with:

```text
number of ingestion jobs
number of supported regions
number of supported providers
number of new/changed titles
```

It should NOT scale directly with:

```text
number of users
page views
filter changes
frontend interactions
```

A user changing runtime from 120 to 90 minutes must cost zero external API calls.

---

# 27. Frontend Product Shape

Possible homepage structure:

```text
--------------------------------------------------

Region: Greece ▼

Netflix ✓
Disney+ ✓
Prime Video ○
Apple TV+ ○

--------------------------------------------------

Ask WatchPulse

"What are you in the mood for?"
[________________________________________]

--------------------------------------------------

Genre
All | Action | Comedy | Drama | Thriller | Sci-Fi

Runtime
Any | <90m | <120m | Custom

Type
Movies | Series | Both

Rating
Any | 6+ | 7+ | 8+

--------------------------------------------------

TOP 10

[1] [2] [3] [4] [5] ...

--------------------------------------------------

NEW RELEASES

[poster] [poster] [poster] ...

--------------------------------------------------

RECENTLY ADDED

[poster] [poster] [poster] ...

--------------------------------------------------

LEAVING SOON

[poster] [poster] [poster] ...

--------------------------------------------------

COMING SOON

[poster] [poster] [poster] ...

--------------------------------------------------
```

All sections must respond to active filters.

Natural-language discovery may alter the active filter state.

Where helpful, show the interpreted constraints as removable chips.

Example:

```text
Netflix ×
Movie ×
Funny ×
Light ×
< 120 min ×
```

---

# 28. Product Differentiation

Do not try to beat JustWatch at being a giant "where to watch" catalog.

WatchPulse should move toward:

> A decision engine for what to watch.

Core product promise:

> Tell WatchPulse what you feel like watching.
> It will search what is actually available on your services in your region.

The natural-language layer should translate human intent into structured discovery.

Examples:

```text
"I have 90 minutes and want something light on Disney+."

"I want a thriller but nothing too scary."

"Something like Interstellar but shorter."

"I feel awful and just want something stupid and funny on Netflix."

"Find me a good non-American movie on Netflix."
```

The local catalog remains the source of truth.

---

# 29. SEO-Friendly Routing

Keep URLs clean and potentially indexable.

Possible routes:

```text
/
 /discover
 /new
 /leaving-soon
 /upcoming

 /gr/netflix
 /gr/netflix/new
 /gr/netflix/leaving-soon

 /us/netflix/new
 /gb/disney-plus/new

 /movie/597-titanic
```

Region/provider pages may become valuable for SEO later.

Do not prematurely build a complicated SEO system, but keep routing compatible with it.

---

# 30. Portfolio Goal

WatchPulse should be a real live product that can be shown to recruiters and hiring managers.

The project should demonstrate:

```text
API ingestion
incremental processing
data modeling
dbt
DuckDB
history tracking
serving-layer design
dynamic querying
backend design
frontend integration
CI/CD
testing
monitoring
cost-awareness
AI integration
```

Prioritize:

```text
live URL
clean UI
working flows
good README
architecture diagram
tests
CI/CD
clear technical decisions
```

Five polished features are better than twenty unfinished ones.

---

# 31. MVP Scope

The initial public version should prioritize the following.

## Data

```text
TMDB integration
Streaming Availability API integration
region support
provider support
daily ingestion
DuckDB storage
dbt transformations
historical streaming events
```

## Filters

```text
region
provider
movie / series
genre
runtime
release year
minimum rating
```

## Sections

```text
Top 10
New Releases
Recently Added
Leaving Soon
Upcoming
```

## Frontend

```text
clean region selector
provider selection
dynamic filters
responsive rails/cards
content details
no login requirement
```

## Engineering

```text
tests
CI
scheduled ingestion
error handling
logging
basic monitoring
```

---

# 32. Explicitly Out of Scope for MVP

Do not build these unless the core product is already working:

```text
Greek TV schedules
linear TV channels
complex user accounts
social features
comments
chat rooms
native mobile apps
advanced collaborative filtering
vector databases unless truly needed
complex ML pipelines
microservices
Kubernetes
real-time streaming ingestion
payments
subscriptions
advertising
affiliate systems
```

Natural-language discovery can be introduced after the deterministic discovery experience works.

If AI is introduced early, keep it strictly bounded as described above.

---

# 33. Coding Principles

Prefer code that is:

```text
simple
typed where practical
testable
modular
source-independent
observable
incremental
easy to replace
```

Prefer small modules with clear responsibilities.

Keep:

```text
API clients
source adapters
transformations
database access
query building
business ranking logic
frontend code
```

separate.

Do not bury business rules inside UI components.

---

# 34. Source Independence

Keep source-specific mappings isolated.

Example:

```text
TMDB API
    ↓
TMDB adapter
    ↓
internal content model
```

and:

```text
Streaming Availability API
    ↓
Streaming adapter
    ↓
internal availability model
```

The rest of the application should depend on the internal models.

If the streaming provider is replaced later, frontend and recommendation logic should require minimal changes.

---

# 35. Configuration

Do not hardcode operational values.

Use configuration/environment variables for:

```text
API keys
default region
supported regions
supported providers
recently-added window
new-release window
leaving-soon window
API base URLs
AI model
AI daily budget
AI rate limits
database path
```

Commit an example environment file.

Do not commit secrets.

---

# 36. Observability

At minimum, scheduled jobs should expose/log:

```text
run start
run end
status
source
rows fetched
rows inserted
rows updated
rows failed
API request count
runtime
error message
```

Failures should be visible.

A broken daily ingestion must not silently leave stale data forever.

Consider persisting pipeline-run metadata.

---

# 37. Data Freshness

The UI should eventually know when data was last refreshed.

Useful internal fields:

```text
source_updated_at
ingested_at
last_successful_refresh_at
```

Do not pretend data is real-time if it is refreshed daily.

---

# 38. Testing Expectations

Add tests for important business behavior.

Examples:

```text
New Release != Recently Added

removed titles are not currently available

upcoming titles are not treated as available

region filtering never leaks titles from another region

provider filtering works correctly

runtime boundaries behave correctly

global filters apply consistently across sections

historical events are preserved

query builder does not allow raw SQL injection
```

Add unit tests for source adapters and ranking logic.

Use fixtures for external API responses.

Do not require live API calls in the normal test suite.

---

# 39. CI/CD

The repository should eventually have CI that checks at least:

```text
formatting
linting
tests
dbt parsing/build where practical
```

Deployment should be reproducible.

Scheduled ingestion should be automated.

GitHub Actions is acceptable for the initial setup.

---

# 40. Performance Principles

Do not prematurely optimize for millions of users.

For MVP:

```text
correctness
simplicity
fast local queries
clean boundaries
```

matter more.

However:

- avoid N+1 external API patterns,
- avoid one external request per frontend interaction,
- batch or cache upstream metadata where practical,
- precompute serving-friendly fields where useful,
- avoid unnecessary repeated transformations.

If scale later requires a different serving database, replace the serving layer without changing the product contract.

---

# 41. Security

Never expose external API secrets or LLM API keys to the frontend.

Use backend-only secrets.

Validate user input.

Use parameterized SQL.

Add rate limiting before exposing AI endpoints publicly.

Do not log secrets.

---

# 42. Development Order

Preferred implementation sequence:

## Phase 1 — Foundation

```text
repository structure
configuration
DuckDB
TMDB client
basic models
tests
```

## Phase 2 — Streaming availability

```text
Streaming Availability API client
provider mappings
region-aware availability
daily ingestion
historical events
```

## Phase 3 — dbt / serving layer

```text
normalized models
serving catalog
quality tests
```

## Phase 4 — Frontend discovery

```text
region selector
provider selection
genre filter
runtime filter
rating filter
Top 10
New Releases
Recently Added
Leaving Soon
Upcoming
```

## Phase 5 — Deployment

```text
live URL
scheduled jobs
monitoring
CI/CD
README
architecture diagram
```

## Phase 6 — Natural language

```text
bounded AI intent parser
structured filters
query execution
usage limits
cost monitoring
kill switch
```

## Phase 7 — Personalization

```text
optional auth
watched
liked
disliked
saved
New For You
```

Do not jump to Phase 7 before the discovery experience is solid.

---

# 43. Definition of a Good MVP

A successful MVP allows a user to:

1. Open WatchPulse without logging in.
2. Select their region.
3. Select one or more streaming platforms.
4. Select movie/series.
5. Filter by genre.
6. Filter by runtime.
7. Filter by release year/rating.
8. See a Top 10 that changes dynamically.
9. See New Releases that respect the same filters.
10. See Recently Added titles.
11. See Upcoming titles.
12. Open a title and see useful metadata.
13. Experience all filter changes without external API calls.

The app should be live, stable, and visually credible enough to put on a CV.

---

# 44. Critical Rules for Coding Agents

When implementing WatchPulse:

1. **Do not trigger external APIs from frontend filter changes.**
2. **Do not make TMDB or Streaming Availability API availability part of the request path for normal browsing.**
3. **Persist upstream data locally.**
4. **Use `tmdb_id` as the primary shared external content identifier whenever possible.**
5. **Always scope streaming availability by region.**
6. **Always scope streaming availability by provider.**
7. **Keep New Releases and Recently Added separate.**
8. **Persist historical streaming events.**
9. **Apply active global filters consistently across all sections.**
10. **Keep raw source schemas away from the frontend.**
11. **Use safe parameterized queries.**
12. **Keep ranking logic replaceable.**
13. **Keep external provider adapters replaceable.**
14. **Do not require login for core discovery.**
15. **Do not turn AI into a general chatbot.**
16. **Do not let the LLM invent streaming availability.**
17. **Do not expose secrets to the browser.**
18. **Do not over-engineer infrastructure before usage requires it.**
19. **Prefer a polished, working live product over additional unfinished features.**
20. **Keep the project understandable enough that a recruiter or engineer can inspect the repo and understand the architecture.**

---

# 45. Guiding Product Statement

When deciding between implementations, prefer the one that best serves this statement:

> WatchPulse helps people decide what to watch by combining their region, streaming services, constraints, and mood with a real, locally queryable streaming catalog.

External APIs build the catalog.

The WatchPulse data layer maintains the catalog.

The query engine answers the question.

The frontend makes the decision easy.
