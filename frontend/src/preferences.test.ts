import { beforeEach, expect, test } from "vitest";
import { loadPreferences, savePreferences } from "./preferences";

beforeEach(() => localStorage.clear());

test("guest preferences round trip through browser storage", () => {
  savePreferences({ region: "GR", providers: ["netflix"] });

  expect(loadPreferences()).toEqual({ region: "GR", providers: ["netflix"] });
});

test("invalid stored preferences safely fall back to empty values", () => {
  localStorage.setItem("watchpulse.discovery-preferences.v1", "not-json");
  expect(loadPreferences()).toEqual({ region: null, providers: [] });
});
