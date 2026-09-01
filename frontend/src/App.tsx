import { useCallback, useEffect, useState } from "react";
import { type CatalogStatus, getCatalogStatus } from "./api/catalog";
import { DiscoverySetup } from "./components/DiscoverySetup";
import { GlobalFilters } from "./components/GlobalFilters";
import { NewReleasesRail } from "./components/NewReleasesRail";
import { RecentlyAddedRail } from "./components/RecentlyAddedRail";
import { TopTenRail } from "./components/TopTenRail";
import { TitleSearch } from "./components/TitleSearch";
import { UpcomingRail } from "./components/UpcomingRail";
import { type CatalogScope, type GlobalFilters as FilterValue } from "./discovery";
import { loadPreferences } from "./preferences";
import "./styles.css";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; status: CatalogStatus }
  | { kind: "error"; message: string };

const formatRefresh = (value: string) => {
  const formatter = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const timeZone = formatter.resolvedOptions().timeZone || "UTC";
  return `${formatter.format(new Date(value))} (${timeZone})`;
};

export default function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [scope, setScope] = useState<CatalogScope | null>(null);
  const [filters, setFilters] = useState<FilterValue>(() => {
    const saved = loadPreferences();
    return {
      contentType: saved.contentType,
      genreIds: saved.genreIds,
      runtimeMax: saved.runtimeMax,
      releaseYearFrom: saved.releaseYearFrom,
      releaseYearTo: saved.releaseYearTo,
      ratingMin: saved.ratingMin,
      language: saved.language,
    };
  });
  const handleScopeChange = useCallback((nextScope: CatalogScope | null) => setScope(nextScope), []);

  useEffect(() => {
    const controller = new AbortController();
    getCatalogStatus(controller.signal)
      .then((status) => setState({ kind: "ready", status }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ kind: "error", message: error instanceof Error ? error.message : "Unable to connect" });
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <main>
      <nav className="nav" aria-label="Primary navigation">
        <a className="brand" href="/" aria-label="WatchPulse home">
          <span className="pulse" aria-hidden="true" />WatchPulse
        </a>
        {state.kind === "ready" ? (
          <span className="freshness"><span className="status-dot" />Updated {formatRefresh(state.status.freshness.latest_source_updated_at)}</span>
        ) : <span className="version">v0.5</span>}
      </nav>
      <div className="app-layout">
        <aside className="discovery-sidebar" aria-label="Discovery controls">
          {state.kind === "loading" && <p className="catalog-notice" aria-live="polite">Connecting to WatchPulse…</p>}
          {state.kind === "error" && <p className="catalog-notice error" role="alert">{state.message}</p>}
          {state.kind === "ready" && <DiscoverySetup onScopeChange={handleScopeChange} />}
          {scope && scope.providers.length > 0 && (
            <GlobalFilters scope={scope} value={filters} onChange={setFilters} />
          )}
        </aside>

        <div className="content-workspace">
          <section className="hero">
            <p className="eyebrow">YOUR STREAM. ONE DECISION.</p>
            <h1>Find your next <span>great watch.</span></h1>
            <p className="intro">WatchPulse searches the catalog available on your services and in your region—without the endless scroll.</p>
          </section>
          {scope && scope.providers.length > 0 && (
            <>
              <TitleSearch scope={scope} filters={filters} />
              <TopTenRail scope={scope} filters={filters} />
              <NewReleasesRail scope={scope} filters={filters} />
              <RecentlyAddedRail scope={scope} filters={filters} />
              <UpcomingRail scope={scope} filters={filters} />
            </>
          )}
          {scope && scope.providers.length === 0 && (
            <p className="selection-prompt">Select at least one streaming service to start discovering titles.</p>
          )}
        </div>
      </div>
      <footer className="credits" aria-label="Credits">
        <a
          className="tmdb-credit"
          href="https://www.themoviedb.org"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Visit The Movie Database"
        >
          <img src="/tmdb-logo.svg" alt="The Movie Database (TMDB)" />
        </a>
        <div>
          <p>This website uses TMDB and the TMDB APIs but is not endorsed, certified, or otherwise approved by TMDB.</p>
          <p>Streaming availability data provided in part by <a href="https://www.justwatch.com" target="_blank" rel="noopener noreferrer">JustWatch</a>.</p>
        </div>
      </footer>
    </main>
  );
}
