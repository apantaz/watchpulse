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
