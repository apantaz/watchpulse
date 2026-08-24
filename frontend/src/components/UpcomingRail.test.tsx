import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { EMPTY_FILTERS } from "../discovery";
import { UpcomingRail } from "./UpcomingRail";

afterEach(() => vi.restoreAllMocks());

const item = {
  tmdb_id: 999,
  content_type: "tv",
  title: "Coming Soon",
  original_title: "Coming Soon",
  overview: "A series announced for a future streaming date.",
  release_date: "2026-09-01",
  release_year: 2026,
  runtime_minutes: 50,
  episode_count: 9,
  season_count: 1,
  original_language: "en",
  genre_ids: [18],
  genre_names: ["Drama"],
  tmdb_rating: null,
  vote_count: 0,
  popularity_score: 20,
  poster_path: "/poster.jpg",
  backdrop_path: null,
  metadata_source: "streaming_availability",
  last_updated_at: "2026-08-23T10:00:00",
  availabilities: [{
    provider_key: "prime_video",
    provider_name: "Prime Video",
    monetization_type: "flatrate",
    available_since: null,
    available_from: "2026-09-03T00:00:00Z",
    expires_on: null,
    is_available: false,
    is_upcoming: true,
    source: "streaming_availability",
    watch_url: null,
  }],
};

test("renders future provider arrivals with their expected date", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [item] }), { status: 200 }),
  );
  render(
    <UpcomingRail
      scope={{ region: "GR", providers: ["prime_video"] }}
      filters={{ ...EMPTY_FILTERS, contentType: "tv" }}
    />,
  );

  expect(screen.getByLabelText("Loading Upcoming")).toBeInTheDocument();
  expect(await screen.findByRole("article", { name: "Coming Soon" })).toBeInTheDocument();
  expect(screen.getByText(/Coming .*2026/)).toBeInTheDocument();
  expect(screen.queryByText("9 episodes")).not.toBeInTheDocument();
  expect(screen.queryByText("1 season", { exact: false })).not.toBeInTheDocument();
  expect(screen.getByText("N/A")).toBeInTheDocument();
  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "upcoming?region=GR&providers=prime_video&content_type=tv",
  );
});

test("shows an honest empty state when no arrivals are announced", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), { status: 200 }),
  );
  render(
    <UpcomingRail
      scope={{ region: "GR", providers: ["prime_video"] }}
      filters={EMPTY_FILTERS}
    />,
  );

  expect(await screen.findByText("No upcoming titles match these filters.")).toBeInTheDocument();
  expect(screen.getByText(/depends on announcements/)).toBeInTheDocument();
});

test("labels an upcoming TV event as a new season when the series is already available", async () => {
  const availableSeries = {
    ...item,
    availabilities: [{
      ...item.availabilities[0],
      is_available: true,
      available_since: "2024-09-19T00:00:00Z",
    }],
  };
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [availableSeries] }), { status: 200 }),
  );

  render(
    <UpcomingRail
      scope={{ region: "GR", providers: ["prime_video"] }}
      filters={{ ...EMPTY_FILTERS, contentType: "tv" }}
    />,
  );

  expect(await screen.findByText(/New season coming .*2026/)).toBeInTheDocument();
  expect(screen.queryByText("Available now")).not.toBeInTheDocument();
});
