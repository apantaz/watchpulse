import { useEffect, useState } from "react";
import { getNewReleases, type CatalogItem } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { TitleCard } from "./TitleCard";

type NewReleasesRailProps = {
  scope: CatalogScope;
  filters: GlobalFilters;
};

type RailState =
  | { kind: "loading" }
  | { kind: "ready"; items: CatalogItem[] }
  | { kind: "error"; message: string };

export function NewReleasesRail({ scope, filters }: NewReleasesRailProps) {
  const [state, setState] = useState<RailState>({ kind: "loading" });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    getNewReleases(scope, filters, controller.signal)
      .then((items) => setState({ kind: "ready", items }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Unable to load New Releases",
          });
        }
      });
    return () => controller.abort();
  }, [scope, filters, retry]);

  return (
    <section
      className="discovery-rail"
      aria-labelledby="new-releases-title"
      aria-busy={state.kind === "loading"}
    >
      <div className="rail-heading">
        <div>
          <p className="status-label">Recently released movies and series</p>
          <h2 id="new-releases-title">New Releases</h2>
        </div>
        {state.kind === "ready" && state.items.length > 0 && <span>{state.items.length} titles</span>}
      </div>

      {state.kind === "loading" && (
        <div className="title-row skeleton-row" aria-label="Loading New Releases">
          {Array.from({ length: 5 }, (_, index) => <div className="card-skeleton" key={index} />)}
        </div>
      )}

      {state.kind === "error" && (
        <div className="rail-message" role="alert">
          <p>{state.message}</p>
          <button type="button" onClick={() => setRetry((value) => value + 1)}>Try again</button>
        </div>
      )}

      {state.kind === "ready" && state.items.length === 0 && (
        <div className="rail-message">
          <p>No recent releases match these filters.</p>
          <span>Try widening the year, genre, runtime, or rating filters.</span>
        </div>
      )}

      {state.kind === "ready" && state.items.length > 0 && (
        <div className="title-row">
          {state.items.map((item) => (
            <TitleCard item={item} key={`${item.content_type}-${item.tmdb_id}`} />
          ))}
        </div>
      )}
    </section>
  );
}
