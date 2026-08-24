import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import type { CatalogItem } from "../api/catalog";
import { TitleCard } from "./TitleCard";

const series: CatalogItem = {
  tmdb_id: 42,
  content_type: "tv",
  title: "Current Series",
  original_title: "Current Series",
  overview: null,
  release_date: "2024-01-01",
  release_year: 2024,
  runtime_minutes: 50,
  episode_count: 9,
  season_count: 1,
  original_language: "en",
  genre_ids: [18],
  genre_names: ["Drama"],
  tmdb_rating: 7.5,
  vote_count: 100,
  popularity_score: 10,
  poster_path: null,
  backdrop_path: null,
  metadata_source: "tmdb",
  last_updated_at: "2026-08-25T00:00:00Z",
  availabilities: [{
    provider_key: "netflix",
    provider_name: "Netflix",
    monetization_type: "subscription",
    available_since: null,
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "tmdb",
    watch_url: null,
  }, {
    provider_key: "disney_plus",
    provider_name: "Disney+",
    monetization_type: "subscription",
    available_since: null,
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "tmdb",
    watch_url: null,
  }, {
    provider_key: "prime_video",
    provider_name: "Prime Video",
    monetization_type: "subscription",
    available_since: null,
    available_from: null,
    expires_on: null,
    is_available: true,
    is_upcoming: false,
    source: "tmdb",
    watch_url: null,
  }],
};

test("shows total episodes for a currently available series", () => {
  render(<TitleCard item={series} />);

  expect(screen.getByText("1 season · 9 episodes", { exact: false })).toBeInTheDocument();
  expect(screen.getByText("★ 7.5")).toBeInTheDocument();
  expect(screen.queryByText("50 min", { exact: false })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Netflix; direct link unavailable")).toHaveAttribute(
    "data-tooltip",
    "Available on this provider, but a direct title link is unavailable.",
  );
  expect(screen.getByLabelText("Disney+; direct link unavailable")).toBeInTheDocument();
  expect(screen.getByLabelText("Prime Video; direct link unavailable")).toBeInTheDocument();
  expect(screen.queryByText("+1")).not.toBeInTheDocument();
});
