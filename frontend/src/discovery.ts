export type ContentType = "movie" | "tv";

export type CatalogScope = {
  region: string;
  providers: string[];
};

export type GlobalFilters = {
  contentType: ContentType | null;
  genreIds: number[];
  runtimeMax: number | null;
  releaseYearFrom: number | null;
  releaseYearTo: number | null;
  ratingMin: number | null;
  language: string | null;
};

export const EMPTY_FILTERS: GlobalFilters = {
  contentType: null,
  genreIds: [],
  runtimeMax: null,
  releaseYearFrom: null,
  releaseYearTo: null,
  ratingMin: null,
  language: null,
};

export function catalogScopeParams(scope: CatalogScope, contentType?: ContentType | null) {
  const params = new URLSearchParams({ region: scope.region });
  scope.providers.forEach((provider) => params.append("providers", provider));
  if (contentType) params.set("content_type", contentType);
  return params;
}

export function discoveryParams(scope: CatalogScope, filters: GlobalFilters) {
  const params = catalogScopeParams(scope, filters.contentType);
  filters.genreIds.forEach((genreId) => params.append("genre_ids", String(genreId)));
  if (filters.runtimeMax !== null) params.set("runtime_max", String(filters.runtimeMax));
  if (filters.releaseYearFrom !== null) params.set("release_year_from", String(filters.releaseYearFrom));
  if (filters.releaseYearTo !== null) params.set("release_year_to", String(filters.releaseYearTo));
  if (filters.ratingMin !== null) params.set("rating_min", String(filters.ratingMin));
  if (filters.language) params.set("language", filters.language);
  return params;
}
