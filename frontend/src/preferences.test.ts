import { beforeEach, expect, test } from "vitest";
import { loadPreferences, savePreferences } from "./preferences";
import { EMPTY_FILTERS } from "./discovery";

beforeEach(() => localStorage.clear());

test("guest preferences round trip through browser storage", () => {
  savePreferences({ region: "GR", providers: ["netflix"] });

  expect(loadPreferences()).toEqual({ region: "GR", providers: ["netflix"], ...EMPTY_FILTERS });
});

test("invalid stored preferences safely fall back to empty values", () => {
  localStorage.setItem("watchpulse.discovery-preferences.v1", "not-json");
  expect(loadPreferences()).toEqual({ region: null, providers: [], ...EMPTY_FILTERS });
});

test("stored numeric filters are bounded and reversed years are repaired", () => {
  localStorage.setItem("watchpulse.discovery-preferences.v1", JSON.stringify({
    runtimeMax: 0,
    ratingMin: 11,
    releaseYearFrom: 2026,
    releaseYearTo: 2020,
    language: "Greek",
  }));

  expect(loadPreferences()).toMatchObject({
    runtimeMax: null,
    ratingMin: null,
    releaseYearFrom: null,
    releaseYearTo: 2020,
    language: null,
  });
});
