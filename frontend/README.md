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

Vite reads `VITE_API_BASE_URL`; copy `.env.example` to `.env.local` only when
the backend is not available at the default `http://127.0.0.1:8000` address.

## Quality commands

```bash
npm run lint
npm run typecheck
npm test
npm run build
```
