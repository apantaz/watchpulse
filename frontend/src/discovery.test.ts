import { expect, test } from "vitest";
import { discoveryParams, type GlobalFilters } from "./discovery";

test("serializes the shared filters using the FastAPI repeated-parameter contract", () => {
  const filters: GlobalFilters = {
    contentType: "movie",
    genreIds: [18, 35],
    runtimeMax: 120,
    releaseYearFrom: 2020,
    releaseYearTo: 2026,
    ratingMin: 7,
    language: "el",
  };

  expect(discoveryParams(
    { region: "GR", providers: ["netflix", "disney_plus"] },
    filters,
  ).toString()).toBe(
    "region=GR&providers=netflix&providers=disney_plus&content_type=movie&genre_ids=18&genre_ids=35&runtime_max=120&release_year_from=2020&release_year_to=2026&rating_min=7&language=el",
  );
});
