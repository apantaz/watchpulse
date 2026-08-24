# WatchPulse frontend

The WatchPulse guest discovery interface is a React, TypeScript, and Vite
single-page application. It calls only the local FastAPI discovery API; it
never calls TMDB or Streaming Availability directly.

## Local development

The frontend requires Node.js 22, which includes `npm`. If `npm` is not found,
install Node.js first. With `nvm`:

```bash
cd frontend
nvm install
nvm use
node --version
npm --version
cd ..
```

Alternatively, install Node.js 22 using the official installer for your
operating system. Python's `requirements.txt` cannot install Node.js or npm.

Start the API from the repository root:

```bash
make dbt-publish
make api-dev
```

In another terminal, install and start the frontend:

```bash
make frontend-install
make frontend-dev
```

Open <http://127.0.0.1:5173>. The initial application shell displays the API
and catalog status to prove the browser-to-backend path is working. Regions and
streaming services are loaded from the local API, and valid guest selections
are remembered in browser-local storage without requiring an account.
Type, genre, runtime, release-year, rating, and language filters use one typed
state and the same query-parameter contract as every FastAPI discovery section.
The Top 10, New Releases, and Recently Added rails query only FastAPI and render
reusable poster cards; ranking badges remain specific to Top 10. Recently Added
uses provider addition time and remains distinct from content release recency.
Upcoming uses future provider arrival evidence and displays the expected date.
An already-available series may also appear there as a new-season announcement.
On desktop, region, provider, and global controls remain in a sticky sidebar
while discovery rails use the wider content workspace. The layout stacks for
touch and narrow screens, and every control still updates local API queries
immediately without an Apply action.
Poster artwork is loaded from TMDB's public image CDN using the ingested
`poster_path`; this is an image asset request, not a TMDB API lookup, and it
uses no API key or discovery quota. Missing or failed images have a local
fallback.

Vite reads `VITE_API_BASE_URL`; copy `.env.example` to `.env.local` only when
the backend is not available at the default `http://127.0.0.1:8000` address.
`VITE_TMDB_IMAGE_BASE_URL` configures the public poster CDN base path.
`VITE_TMDB_PROVIDER_IMAGE_BASE_URL` configures the smaller provider-logo path.
The four launch providers currently use an explicit frontend logo adapter;
unknown providers receive a fallback. A later reference-ingestion increment
will move `logo_path` into the provider dimension and API contract.
Provider badges become external links only when the API returns a verified
HTTPS `watch_url` retained from Streaming Availability. Unlinked badges mean
availability is known but no authoritative title destination is currently
stored; the frontend never guesses provider URLs.

## Quality commands

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
