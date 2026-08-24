import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { TitleSearch } from "./TitleSearch";
import { EMPTY_FILTERS } from "../discovery";

afterEach(() => vi.restoreAllMocks());

test("searches the selected local catalog after two characters", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({
      items: [{
        tmdb_id: 42,
        content_type: "movie",
        title: "Monsters",
        original_title: "Monsters",
        overview: null,
        release_date: "2024-01-01",
        release_year: 2024,
        runtime_minutes: 100,
        original_language: "en",
        genre_ids: [18],
        genre_names: ["Drama"],
        tmdb_rating: 7.2,
        vote_count: 100,
        popularity_score: 20,
        poster_path: "/poster.jpg",
        backdrop_path: null,
        metadata_source: "tmdb",
        last_updated_at: "2026-08-25T10:00:00Z",
        availabilities: [{ provider_name: "Netflix" }],
      }],
    }), { status: 200 }),
  );
  render(
    <TitleSearch
      scope={{ region: "GR", providers: ["netflix"] }}
      filters={EMPTY_FILTERS}
    />,
  );

  const searchbox = screen.getByRole("searchbox");
  fireEvent.focus(searchbox);
  fireEvent.change(searchbox, { target: { value: "Mon" } });
  expect(await screen.findByText("Monsters", {}, { timeout: 1500 })).toBeInTheDocument();
  expect(screen.getByText("Netflix")).toBeInTheDocument();
  expect(screen.getByText("7.2")).toHaveClass("search-rating");
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  const url = String(fetchMock.mock.calls[0][0]);
  expect(url).toContain("query=Mon");
  expect(url).toContain("region=GR");
  expect(url).toContain("providers=netflix");
});

test("does not request a one-character query", () => {
  const fetchMock = vi.spyOn(globalThis, "fetch");
  render(
    <TitleSearch
      scope={{ region: "GR", providers: ["netflix"] }}
      filters={EMPTY_FILTERS}
    />,
  );
  fireEvent.change(screen.getByRole("searchbox"), { target: { value: "M" } });
  expect(fetchMock).not.toHaveBeenCalled();
});

test("makes the active search filters visible", () => {
  render(
    <TitleSearch
      scope={{ region: "GR", providers: ["netflix", "disney_plus"] }}
      filters={{
        ...EMPTY_FILTERS,
        contentType: "tv",
        runtimeMax: 120,
        ratingMin: 7,
        language: "en",
      }}
    />,
  );

  expect(screen.getByText(/Searching within:/).closest("p")).toHaveTextContent(
    "GR · 2 services · Series · Up to 120 min · Rating 7+ · EN",
  );
});
