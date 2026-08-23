import { useEffect, useState } from "react";
import { type CatalogStatus, getCatalogStatus } from "./api/catalog";
import { DiscoverySetup } from "./components/DiscoverySetup";
import "./styles.css";

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; status: CatalogStatus }
  | { kind: "error"; message: string };

const formatRefresh = (value: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(value),
  );

export default function App() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

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
        <span className="version">v0.5 preview</span>
      </nav>
      <section className="hero">
        <p className="eyebrow">YOUR STREAMS. ONE DECISION.</p>
        <h1>Find your next<br /><span>great watch.</span></h1>
        <p className="intro">WatchPulse searches the catalog available on your services and in your region—without the endless scroll.</p>
      </section>
      <section className="status-card" aria-live="polite">
        <div>
          <p className="status-label">Local discovery catalog</p>
          {state.kind === "loading" && <h2>Connecting to WatchPulse…</h2>}
          {state.kind === "error" && <h2>{state.message}</h2>}
          {state.kind === "ready" && <h2>Ready for discovery</h2>}
        </div>
        {state.kind === "loading" && <span className="status-dot loading" aria-label="Loading" />}
        {state.kind === "error" && <span className="status-dot error" aria-label="Offline" />}
        {state.kind === "ready" && (
          <div className="catalog-summary">
            <span className="status-dot" aria-label="Online" />
            <strong>{state.status.freshness.current_row_count.toLocaleString()}</strong>
            <span>available titles</span>
            <small>Refreshed {formatRefresh(state.status.freshness.latest_source_updated_at)}</small>
          </div>
        )}
      </section>
      {state.kind === "ready" && <DiscoverySetup />}
      <p className="coming-next">Global filters and discovery rails arrive in the next increment.</p>
    </main>
  );
}
