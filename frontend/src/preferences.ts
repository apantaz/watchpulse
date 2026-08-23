import { EMPTY_FILTERS, type GlobalFilters } from "./discovery";

export type GuestPreferences = GlobalFilters & {
  region: string | null;
  providers: string[];
};

const STORAGE_KEY = "watchpulse.discovery-preferences.v1";
const EMPTY_PREFERENCES: GuestPreferences = {
  region: null,
  providers: [],
  ...EMPTY_FILTERS,
};

const boundedNumber = (value: unknown, minimum: number, maximum: number) =>
  typeof value === "number" && value >= minimum && value <= maximum ? value : null;

export function loadPreferences(storage: Storage = localStorage): GuestPreferences {
  try {
    const value: unknown = JSON.parse(storage.getItem(STORAGE_KEY) ?? "null");
    if (!value || typeof value !== "object") return EMPTY_PREFERENCES;
    const candidate = value as Record<string, unknown>;
    const releaseYearFrom = boundedNumber(candidate.releaseYearFrom, 1870, 2200);
    const releaseYearTo = boundedNumber(candidate.releaseYearTo, 1870, 2200);
    return {
      region: typeof candidate.region === "string" ? candidate.region : null,
      providers: Array.isArray(candidate.providers)
        ? candidate.providers.filter((provider): provider is string => typeof provider === "string")
        : [],
      contentType: candidate.contentType === "movie" || candidate.contentType === "tv"
        ? candidate.contentType
        : null,
      genreIds: Array.isArray(candidate.genreIds)
        ? candidate.genreIds.filter((genreId): genreId is number => Number.isInteger(genreId) && genreId > 0)
        : [],
      runtimeMax: boundedNumber(candidate.runtimeMax, 1, 1440),
      releaseYearFrom: releaseYearFrom !== null && releaseYearTo !== null && releaseYearFrom > releaseYearTo ? null : releaseYearFrom,
      releaseYearTo,
      ratingMin: boundedNumber(candidate.ratingMin, 0, 10),
      language: typeof candidate.language === "string" && /^[a-z]{2,3}$/.test(candidate.language)
        ? candidate.language
        : null,
    };
  } catch {
    return EMPTY_PREFERENCES;
  }
}

export function savePreferences(
  preferences: Partial<GuestPreferences>,
  storage: Storage = localStorage,
) {
  storage.setItem(STORAGE_KEY, JSON.stringify({ ...loadPreferences(storage), ...preferences }));
}
