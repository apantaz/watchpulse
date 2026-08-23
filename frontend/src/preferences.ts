export type GuestPreferences = {
  region: string | null;
  providers: string[];
};

const STORAGE_KEY = "watchpulse.discovery-preferences.v1";
const EMPTY_PREFERENCES: GuestPreferences = { region: null, providers: [] };

export function loadPreferences(storage: Storage = localStorage): GuestPreferences {
  try {
    const value: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? "null");
    if (!value || typeof value !== "object") return EMPTY_PREFERENCES;
    const candidate = value as Record<string, unknown>;
    return {
      region: typeof candidate.region === "string" ? candidate.region : null,
      providers: Array.isArray(candidate.providers)
        ? candidate.providers.filter((provider): provider is string => typeof provider === "string")
        : [],
    };
  } catch {
    return EMPTY_PREFERENCES;
  }
}

export function savePreferences(preferences: GuestPreferences, storage: Storage = localStorage) {
  storage.setItem(STORAGE_KEY, JSON.stringify(preferences));
}
