import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { EMPTY_FILTERS } from "../discovery";
import { TopTenRail } from "./TopTenRail";

afterEach(() => vi.restoreAllMocks());

const item = {
  tmdb_id: 634649,
  content_type: "movie",
  title: "Spider-Man: No Way Home",
  original_title: "Spider-Man: No Way Home",
  overview: "A multiverse adventure.",
  release_date: "2021-12-15",
  release_year: 2021,
  runtime_minutes: 148,
  original_language: "en",
  genre_ids: [28],
  genre_names: ["Action", "Adventure"],
  tmdb_rating: 8.0,
  vote_count: 22000,
  popularity_score: 100,
  poster_path: null,
  backdrop_path: null,
  metadata_source: "tmdb",
  last_updated_at: "2026-08-23T10:00:00",
  availabilities: [{
    provider_key: "netflix",
    provider_name: "Netflix",
    monetization_type: "flatrate",
    available_since: null,
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "tmdb",
    watch_url: "https://www.netflix.com/title/81727396",
  }],
  rank: 1,
};

const success = () => Promise.resolve(new Response(JSON.stringify({ items: [item] }), { status: 200 }));

test("renders ranked local catalog results and sends every active filter", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(success);
  render(
    <TopTenRail
      scope={{ region: "GR", providers: ["netflix"] }}
      filters={{ ...EMPTY_FILTERS, contentType: "movie", genreIds: [28], ratingMin: 7 }}
    />,
  );

  expect(screen.getByLabelText("Loading Top 10")).toBeInTheDocument();
  expect(await screen.findByRole("article", { name: /Number 1.*Spider-Man/ })).toBeInTheDocument();
  expect(screen.getByText("Netflix")).toBeInTheDocument();
  expect(screen.getByText("2021 · Movie · 148 min")).toBeInTheDocument();
  expect(screen.getByText("Action · Adventure")).toBeInTheDocument();
  expect(screen.getByText("A multiverse adventure.")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View Spider-Man: No Way Home on TMDB" })).toHaveAttribute(
    "href",
    "https://www.themoviedb.org/movie/634649",
  );
  expect(screen.getByRole("link", { name: "Open Spider-Man: No Way Home on Netflix" })).toHaveAttribute(
    "href",
    "https://www.netflix.com/title/81727396",
  );
  expect(String(fetchMock.mock.calls[0][0])).toContain(
    "region=GR&providers=netflix&content_type=movie&genre_ids=28&rating_min=7",
  );
});

test("shows an actionable empty result", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ items: [] }), { status: 200 }),
  );
  render(<TopTenRail scope={{ region: "GR", providers: ["netflix"] }} filters={EMPTY_FILTERS} />);
  expect(await screen.findByText("Nothing matches all these filters.")).toBeInTheDocument();
});

test("offers a retry after a section request fails", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockRejectedValueOnce(new Error("Connection lost"))
    .mockImplementationOnce(success);
  render(<TopTenRail scope={{ region: "GR", providers: ["netflix"] }} filters={EMPTY_FILTERS} />);

  expect(await screen.findByText("Connection lost")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("Spider-Man: No Way Home")).toBeInTheDocument();
});
