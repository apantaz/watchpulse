import { useEffect, useState } from "react";
import type { CatalogItem } from "../api/catalog";
import type { CatalogScope, GlobalFilters } from "../discovery";
import { TitleCard } from "./TitleCard";

type CatalogLoader = (
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
) => Promise<CatalogItem[]>;

type CatalogRailProps = {
  id: string;
  title: string;
  subtitle: string;
  loadingLabel: string;
  emptyTitle: string;
  emptyHint: string;
  errorFallback: string;
  scope: CatalogScope;
  filters: GlobalFilters;
  load: CatalogLoader;
};

type RailState =
  | { kind: "loading" }
  | { kind: "ready"; items: CatalogItem[] }
  | { kind: "error"; message: string };

export function CatalogRail({
  id,
  title,
  subtitle,
  loadingLabel,
  emptyTitle,
  emptyHint,
  errorFallback,
  scope,
  filters,
  load,
}: CatalogRailProps) {
  const [state, setState] = useState<RailState>({ kind: "loading" });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: "loading" });
    load(scope, filters, controller.signal)
      .then((items) => setState({ kind: "ready", items }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : errorFallback,
          });
        }
      });
    return () => controller.abort();
  }, [scope, filters, retry, load, errorFallback]);

  return (
    <section className="discovery-rail" aria-labelledby={id} aria-busy={state.kind === "loading"}>
      <div className="rail-heading">
        <div>
          <p className="status-label">{subtitle}</p>
          <h2 id={id}>{title}</h2>
        </div>
        {state.kind === "ready" && state.items.length > 0 && <span>{state.items.length} titles</span>}
      </div>

      {state.kind === "loading" && (
        <div className="title-row skeleton-row" aria-label={loadingLabel}>
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
          <p>{emptyTitle}</p>
          <span>{emptyHint}</span>
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
