import {
  catalogScopeParams,
  discoveryParams,
  type CatalogScope,
  type ContentType,
  type GlobalFilters,
} from "../discovery";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000").replace(
  /\/$/,
  "",
);

export type CatalogFreshness = {
  catalog_name: string;
  warehouse_built_at: string;
  latest_source_updated_at: string;
  catalog_row_count: number;
  current_row_count: number;
  upcoming_row_count: number;
};

export type CatalogStatus = { api: "online"; freshness: CatalogFreshness };
export type RegionOption = { code: string };
export type ProviderOption = { key: string; name: string };
export type GenreOption = { content_type: string; id: number; name: string };
export type FilterOptions = {
  content_types: string[];
  languages: string[];
  runtime_minutes: { minimum: number | null; maximum: number | null };
  release_year: { minimum: number | null; maximum: number | null };
  rating: { minimum: number | null; maximum: number | null };
};
export type Availability = {
  provider_key: string;
  provider_name: string;
  monetization_type: string;
  available_since: string | null;
  available_from: string | null;
  expires_on: string | null;
  is_available: boolean;
  is_upcoming: boolean;
  source: string;
  watch_url: string | null;
};
export type CatalogItem = {
  tmdb_id: number;
  content_type: string;
  title: string;
  original_title: string | null;
  overview: string | null;
  release_date: string | null;
  release_year: number | null;
  runtime_minutes: number | null;
  episode_count?: number | null;
  season_count?: number | null;
  original_language: string | null;
  genre_ids: number[];
  genre_names: string[];
  tmdb_rating: number | null;
  vote_count: number | null;
  popularity_score: number | null;
  poster_path: string | null;
  backdrop_path: string | null;
  metadata_source: string;
  last_updated_at: string;
  availabilities: Availability[];
};
export type RankedCatalogItem = CatalogItem & { rank: number };

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
    signal,
  });
  if (!response.ok) {
    throw new Error(response.status === 503 ? "Catalog is not published yet" : "API unavailable");
  }
  return (await response.json()) as T;
}

export async function getCatalogStatus(signal?: AbortSignal): Promise<CatalogStatus> {
  const [health, freshness] = await Promise.all([
    getJson<{ status: string }>("/health", signal),
    getJson<CatalogFreshness>("/api/v1/catalog/freshness", signal),
  ]);
  if (health.status !== "ok") throw new Error("API health check failed");
  return { api: "online", freshness };
}

export async function getRegions(signal?: AbortSignal): Promise<RegionOption[]> {
  const response = await getJson<{ regions: RegionOption[] }>("/api/v1/catalog/regions", signal);
  return response.regions;
}

export async function getProviders(
  region: string,
  signal?: AbortSignal,
): Promise<ProviderOption[]> {
  const params = new URLSearchParams({ region });
  const response = await getJson<{ providers: ProviderOption[] }>(
    `/api/v1/catalog/providers?${params}`,
    signal,
  );
  return response.providers;
}

export async function getGenres(
  scope: CatalogScope,
  contentType: ContentType | null,
  signal?: AbortSignal,
): Promise<GenreOption[]> {
  const response = await getJson<{ genres: GenreOption[] }>(
    `/api/v1/catalog/genres?${catalogScopeParams(scope, contentType)}`,
    signal,
  );
  return [...new Map(response.genres.map((genre) => [genre.id, genre])).values()];
}

export async function getFilterOptions(
  scope: CatalogScope,
  contentType: ContentType | null,
  signal?: AbortSignal,
): Promise<FilterOptions> {
  return getJson<FilterOptions>(
    `/api/v1/catalog/filter-options?${catalogScopeParams(scope, contentType)}`,
    signal,
  );
}

export async function getTopTen(
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
): Promise<RankedCatalogItem[]> {
  const response = await getJson<{ items: RankedCatalogItem[] }>(
    `/api/v1/discovery/top-10?${discoveryParams(scope, filters)}`,
    signal,
  );
  return response.items;
}

export async function getNewReleases(
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
): Promise<CatalogItem[]> {
  const response = await getJson<{ items: CatalogItem[] }>(
    `/api/v1/discovery/new-releases?${discoveryParams(scope, filters)}`,
    signal,
  );
  return response.items;
}

export async function getRecentlyAdded(
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
): Promise<CatalogItem[]> {
  const response = await getJson<{ items: CatalogItem[] }>(
    `/api/v1/discovery/recently-added?${discoveryParams(scope, filters)}`,
    signal,
  );
  return response.items;
}

export async function getUpcoming(
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
): Promise<CatalogItem[]> {
  const response = await getJson<{ items: CatalogItem[] }>(
    `/api/v1/discovery/upcoming?${discoveryParams(scope, filters)}`,
    signal,
  );
  return response.items;
}

export async function searchTitles(
  query: string,
  scope: CatalogScope,
  filters: GlobalFilters,
  signal?: AbortSignal,
): Promise<CatalogItem[]> {
  const params = discoveryParams(scope, filters);
  params.set("query", query);
  const response = await getJson<{ items: CatalogItem[] }>(
    `/api/v1/discovery/search?${params}`,
    signal,
  );
  return response.items;
}
