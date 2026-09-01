import { useEffect, useId, useRef, useState } from "react";
import { searchTitles, type CatalogItem } from "../api/catalog";
import { type CatalogScope, type GlobalFilters } from "../discovery";

type Props = { scope: CatalogScope; filters: GlobalFilters };

const posterUrl = (path: string | null) =>
  path ? `https://image.tmdb.org/t/p/w92${path}` : null;

export function TitleSearch({ scope, filters }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CatalogItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [focused, setFocused] = useState(false);
  const blurTimer = useRef<number | undefined>(undefined);
  const listboxId = useId();
  const normalized = query.trim();
  const activeScope = [
    scope.region,
    `${scope.providers.length} ${scope.providers.length === 1 ? "service" : "services"}`,
    filters.contentType === "movie" ? "Movies" : filters.contentType === "tv" ? "Series" : "Movies & series",
    filters.genreIds.length ? `${filters.genreIds.length} ${filters.genreIds.length === 1 ? "genre" : "genres"}` : null,
    filters.runtimeMax !== null ? `Up to ${filters.runtimeMax} min` : null,
    filters.releaseYearFrom !== null || filters.releaseYearTo !== null
      ? `${filters.releaseYearFrom ?? "Any"}–${filters.releaseYearTo ?? "Now"}`
      : null,
    filters.ratingMin !== null ? `Rating ${filters.ratingMin}+` : null,
    filters.language ? filters.language.toUpperCase() : null,
  ].filter((value): value is string => value !== null);

  useEffect(() => {
    if (normalized.length < 2) {
      setResults([]);
      setStatus("idle");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setStatus("loading");
      searchTitles(normalized, scope, filters, controller.signal)
        .then((items) => {
          setResults(items);
          setStatus("ready");
        })
        .catch(() => {
          if (!controller.signal.aborted) setStatus("error");
        });
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [normalized, scope, filters]);

  const open = focused && normalized.length >= 2;
  return (
    <div className="title-search" role="search">
      <label htmlFor="catalog-title-search">Search the catalog</label>
      <div className="search-input-wrap">
        <span aria-hidden="true">⌕</span>
        <input
          id="catalog-title-search"
          type="search"
          value={query}
          placeholder="Search by title…"
          autoComplete="off"
          aria-controls={listboxId}
          aria-expanded={open}
          aria-autocomplete="list"
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => {
            window.clearTimeout(blurTimer.current);
            setFocused(true);
          }}
          onBlur={() => {
            blurTimer.current = window.setTimeout(() => setFocused(false), 120);
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape") setFocused(false);
          }}
        />
        {status === "loading" && <span className="search-spinner" aria-label="Searching" />}
      </div>
      <p className="search-scope">
        <strong>Searching within:</strong> {activeScope.join(" · ")}
      </p>
      {open && (
        <div className="search-results" id={listboxId} role="listbox" aria-label="Title results">
          {status === "ready" && results.length === 0 && (
            <p>No titles match this search and your active filters.</p>
          )}
          {status === "error" && <p>Search is temporarily unavailable.</p>}
          {results.map((item) => {
            const image = posterUrl(item.poster_path);
            return (
              <a
                key={`${item.content_type}-${item.tmdb_id}`}
                role="option"
                aria-selected="false"
                aria-label={`View details for ${item.title} on TMDB`}
                href={`https://www.themoviedb.org/${item.content_type}/${item.tmdb_id}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                {image ? <img src={image} alt="" /> : <span className="search-poster-fallback">{item.title[0]}</span>}
                <span className="search-result-copy">
                  <strong>{item.title}</strong>
                  <small>{[item.release_year, item.genre_names.slice(0, 2).join(", ")].filter(Boolean).join(" · ")}</small>
                  <small>{item.availabilities.map((entry) => entry.provider_name).filter((name, index, names) => names.indexOf(name) === index).join(", ")}</small>
                  <small className="search-tmdb-link">View details on TMDB ↗</small>
                </span>
                <span className={item.tmdb_rating && item.tmdb_rating > 0 ? "search-rating" : "search-rating unrated"}>
                  <span aria-hidden="true">★</span>{item.tmdb_rating && item.tmdb_rating > 0 ? item.tmdb_rating.toFixed(1) : "N/A"}
                </span>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}
