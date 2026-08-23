import { useEffect, useRef, useState } from "react";
import { getFilterOptions, getGenres, type FilterOptions, type GenreOption } from "../api/catalog";
import { EMPTY_FILTERS, type CatalogScope, type ContentType, type GlobalFilters as FilterValue } from "../discovery";
import { savePreferences } from "../preferences";

type GlobalFiltersProps = {
  scope: CatalogScope;
  value: FilterValue;
  onChange: (filters: FilterValue) => void;
};

type ReferenceState =
  | { kind: "loading" }
  | { kind: "ready"; genres: GenreOption[]; options: FilterOptions }
  | { kind: "error"; message: string };

const update = <K extends keyof FilterValue>(
  value: FilterValue,
  key: K,
  next: FilterValue[K],
) => ({ ...value, [key]: next });

const numberOrNull = (value: string) => value === "" ? null : Number(value);

export function GlobalFilters({ scope, value, onChange }: GlobalFiltersProps) {
  const [references, setReferences] = useState<ReferenceState>({ kind: "loading" });
  const valueRef = useRef(value);
  const onChangeRef = useRef(onChange);
  valueRef.current = value;
  onChangeRef.current = onChange;
  const region = scope.region;
  const providers = scope.providers;
  const contentType = value.contentType;

  useEffect(() => {
    const controller = new AbortController();
    setReferences({ kind: "loading" });
    Promise.all([
      getGenres({ region, providers }, contentType, controller.signal),
      getFilterOptions({ region, providers }, contentType, controller.signal),
    ])
      .then(([genres, options]) => {
        const validGenres = new Set(genres.map(({ id }) => id));
        const current = valueRef.current;
        const nextGenreIds = current.genreIds.filter((id) => validGenres.has(id));
        if (nextGenreIds.length !== current.genreIds.length) {
          onChangeRef.current({ ...current, genreIds: nextGenreIds });
        }
        setReferences({ kind: "ready", genres, options });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setReferences({ kind: "error", message: error instanceof Error ? error.message : "Unable to load filters" });
        }
      });
    return () => controller.abort();
  }, [region, providers, contentType]);

  useEffect(() => savePreferences(value), [value]);

  const setContentType = (contentType: ContentType | null) =>
    onChange({ ...value, contentType, genreIds: [] });

  const toggleGenre = (genreId: number) =>
    onChange({
      ...value,
      genreIds: value.genreIds.includes(genreId)
        ? value.genreIds.filter((id) => id !== genreId)
        : [...value.genreIds, genreId],
    });

  const setReleaseYearFrom = (next: number | null) => onChange({
    ...value,
    releaseYearFrom: next,
    releaseYearTo: next !== null && value.releaseYearTo !== null && next > value.releaseYearTo
      ? null
      : value.releaseYearTo,
  });

  const setReleaseYearTo = (next: number | null) => onChange({
    ...value,
    releaseYearFrom: next !== null && value.releaseYearFrom !== null && next < value.releaseYearFrom
      ? null
      : value.releaseYearFrom,
    releaseYearTo: next,
  });

  return (
    <section className="global-filters" aria-labelledby="filters-title">
      <div className="setup-heading">
        <div>
          <p className="status-label">Refine your choice</p>
          <h2 id="filters-title">What are you looking for?</h2>
        </div>
        <button className="clear-filters" type="button" onClick={() => onChange(EMPTY_FILTERS)}>
          Clear filters
        </button>
      </div>

      <div className="filter-grid">
        <fieldset className="filter-group type-filter">
          <legend>Type</legend>
          <div className="segmented-control">
            {([null, "movie", "tv"] as const).map((type) => (
              <button
                type="button"
                key={type ?? "all"}
                aria-pressed={value.contentType === type}
                onClick={() => setContentType(type)}
              >
                {type === null ? "All" : type === "movie" ? "Movies" : "Series"}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="filter-group">
          <span>Runtime</span>
          <select value={value.runtimeMax ?? ""} onChange={(event) => onChange(update(value, "runtimeMax", numberOrNull(event.target.value)))}>
            <option value="">Any length</option>
            <option value="90">Up to 90 min</option>
            <option value="120">Up to 2 hours</option>
            <option value="180">Up to 3 hours</option>
          </select>
        </label>

        <label className="filter-group">
          <span>Minimum rating</span>
          <select value={value.ratingMin ?? ""} onChange={(event) => onChange(update(value, "ratingMin", numberOrNull(event.target.value)))}>
            <option value="">Any rating</option>
            <option value="6">6+</option>
            <option value="7">7+</option>
            <option value="8">8+</option>
          </select>
        </label>

        <label className="filter-group">
          <span>Language</span>
          <select
            value={value.language ?? ""}
            disabled={references.kind !== "ready"}
            onChange={(event) => onChange(update(value, "language", event.target.value || null))}
          >
            <option value="">Any language</option>
            {references.kind === "ready" && references.options.languages.map((language) => (
              <option key={language} value={language}>{language.toUpperCase()}</option>
            ))}
          </select>
        </label>

        <div className="filter-group year-filter">
          <span>Release year</span>
          <div>
            <input
              aria-label="Release year from"
              type="number"
              placeholder={references.kind === "ready" ? String(references.options.release_year.minimum ?? "From") : "From"}
              min="1870"
              max="2200"
              value={value.releaseYearFrom ?? ""}
              onChange={(event) => setReleaseYearFrom(numberOrNull(event.target.value))}
            />
            <span>to</span>
            <input
              aria-label="Release year to"
              type="number"
              placeholder={references.kind === "ready" ? String(references.options.release_year.maximum ?? "To") : "To"}
              min="1870"
              max="2200"
              value={value.releaseYearTo ?? ""}
              onChange={(event) => setReleaseYearTo(numberOrNull(event.target.value))}
            />
          </div>
        </div>
      </div>

      <fieldset className="genre-filter" disabled={references.kind !== "ready"}>
        <legend>Genres</legend>
        <div className="genre-list">
          {references.kind === "ready" && references.genres.map((genre) => (
            <button
              type="button"
              key={`${genre.content_type}-${genre.id}`}
              aria-pressed={value.genreIds.includes(genre.id)}
              onClick={() => toggleGenre(genre.id)}
            >
              {genre.name}
            </button>
          ))}
        </div>
      </fieldset>

      {references.kind === "loading" && <p className="setup-loading">Loading filter options…</p>}
      {references.kind === "error" && <p className="setup-error" role="alert">{references.message}</p>}
    </section>
  );
}
