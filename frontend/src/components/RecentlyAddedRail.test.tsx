import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { EMPTY_FILTERS } from "../discovery";
import { RecentlyAddedRail } from "./RecentlyAddedRail";

afterEach(() => vi.restoreAllMocks());

const item = {
  tmdb_id: 597,
  content_type: "movie",
  title: "An Older Film",
  original_title: "An Older Film",
  overview: "An established title newly added to a provider.",
  release_date: "1997-11-18",
  release_year: 1997,
  runtime_minutes: 194,
  original_language: "en",
  genre_ids: [18],
  genre_names: ["Drama"],
  tmdb_rating: 7.9,
  vote_count: 26000,
  popularity_score: 90,
  poster_path: "/poster.jpg",
  backdrop_path: null,
  metadata_source: "tmdb",
  last_updated_at: "2026-08-23T10:00:00",
  availabilities: [{
    provider_key: "netflix",
    provider_name: "Netflix",
    monetization_type: "flatrate",
    available_since: "2026-08-22T10:00:00",
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "streaming_availability",
    watch_url: "https://www.netflix.com/title/123",
  }],
};

test("renders provider arrivals independently of the content release year", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [item] }), { status: 200 }),
  );
  render(
    <RecentlyAddedRail
      scope={{ region: "GR", providers: ["netflix"] }}
      filters={{ ...EMPTY_FILTERS, contentType: "movie" }}
    />,
  );

  expect(screen.getByLabelText("Loading Recently Added")).toBeInTheDocument();
  expect(await screen.findByRole("article", { name: "An Older Film" })).toBeInTheDocument();
  expect(screen.getByText("1997 · Movie · 194 min")).toBeInTheDocument();
  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "recently-added?region=GR&providers=netflix&content_type=movie",
  );
});

test("shows the Recently Added empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), { status: 200 }),
  );
  render(
    <RecentlyAddedRail
      scope={{ region: "GR", providers: ["netflix"] }}
      filters={EMPTY_FILTERS}
    />,
  );

  expect(
    await screen.findByText("No recently added titles match these filters."),
  ).toBeInTheDocument();
});
