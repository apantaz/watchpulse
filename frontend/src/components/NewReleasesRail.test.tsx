import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { EMPTY_FILTERS } from "../discovery";
import { NewReleasesRail } from "./NewReleasesRail";

afterEach(() => vi.restoreAllMocks());

const item = {
  tmdb_id: 123,
  content_type: "movie",
  title: "A New Release",
  original_title: "A New Release",
  overview: "A newly released story.",
  release_date: "2026-08-20",
  release_year: 2026,
  runtime_minutes: 104,
  original_language: "en",
  genre_ids: [18],
  genre_names: ["Drama"],
  tmdb_rating: 7.4,
  vote_count: 500,
  popularity_score: 80,
  poster_path: "/poster.jpg",
  backdrop_path: null,
  metadata_source: "tmdb",
  last_updated_at: "2026-08-23T10:00:00",
  availabilities: [{
    provider_key: "disney_plus",
    provider_name: "Disney+",
    monetization_type: "flatrate",
    available_since: null,
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "tmdb",
    watch_url: null,
  }],
};

const success = () => Promise.resolve(
  new Response(JSON.stringify({ items: [item] }), { status: 200 }),
);

test("renders unranked new releases and sends the shared filters", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(success);
  render(
    <NewReleasesRail
      scope={{ region: "GR", providers: ["disney_plus"] }}
      filters={{ ...EMPTY_FILTERS, contentType: "movie", genreIds: [18] }}
    />,
  );

  expect(screen.getByLabelText("Loading New Releases")).toBeInTheDocument();
  expect(await screen.findByRole("article", { name: "A New Release" })).toBeInTheDocument();
  expect(screen.queryByText("1")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Disney+; direct link unavailable")).toHaveAttribute(
    "data-tooltip",
    "Available on this provider, but a direct title link is unavailable.",
  );
  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "new-releases?region=GR&providers=disney_plus&content_type=movie&genre_ids=18",
  );
});

test("shows a section-specific empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), { status: 200 }),
  );
  render(
    <NewReleasesRail
      scope={{ region: "GR", providers: ["disney_plus"] }}
      filters={EMPTY_FILTERS}
    />,
  );
  expect(await screen.findByText("No recent releases match these filters.")).toBeInTheDocument();
});

test("offers a retry when the New Releases request fails", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new Error("Connection lost"))
    .mockImplementationOnce(success);
  render(
    <NewReleasesRail
      scope={{ region: "GR", providers: ["disney_plus"] }}
      filters={EMPTY_FILTERS}
    />,
  );

  expect(await screen.findByText("Connection lost")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("A New Release")).toBeInTheDocument();
});
