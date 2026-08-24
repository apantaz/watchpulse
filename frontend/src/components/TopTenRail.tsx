import { useEffect, useState } from "react";
import { getTopTen, type RankedCatalogItem } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { TitleCard } from "./TitleCard";

type TopTenRailProps = {
  scope: CatalogScope;
  filters: GlobalFilters;
};

type RailState =
  | { kind: "loading" }
  | { kind: "ready"; items: RankedCatalogItem[] }
  | { kind: "error"; message: string };

export function TopTenRail({ scope, filters }: TopTenRailProps) {
  const [state, setState] = useState<RailState>({ kind: "loading" });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    getTopTen(scope, filters, controller.signal)
      .then((items) => setState({ kind: "ready", items }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ kind: "error", message: error instanceof Error ? error.message : "Unable to load Top 10" });
        }
      });
    return () => controller.abort();
  }, [scope, filters, retry]);

  return (
    <section className="discovery-rail" aria-labelledby="top-ten-title" aria-busy={state.kind === "loading"}>
      <div className="rail-heading">
        <h2 id="top-ten-title">Top 10</h2>
        {state.kind === "ready" && state.items.length > 0 && <span>{state.items.length} titles</span>}
      </div>

      {state.kind === "loading" && (
        <div className="title-row skeleton-row" aria-label="Loading Top 10">
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
          <p>Nothing matches all these filters.</p>
          <span>Try removing a genre, runtime, or rating filter.</span>
        </div>
      )}

      {state.kind === "ready" && state.items.length > 0 && (
        <div className="title-row">
          {state.items.map((item) => <TitleCard item={item} rank={item.rank} key={`${item.content_type}-${item.tmdb_id}`} />)}
        </div>
      )}
    </section>
  );
}
