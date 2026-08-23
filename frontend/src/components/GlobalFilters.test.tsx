import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, test, vi } from "vitest";
import { EMPTY_FILTERS, type GlobalFilters as FilterValue } from "../discovery";
import { GlobalFilters } from "./GlobalFilters";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const response = (value: unknown) =>
  Promise.resolve(new Response(JSON.stringify(value), { status: 200 }));
const SCOPE = { region: "GR", providers: ["netflix"] };

function Harness() {
  const [filters, setFilters] = useState<FilterValue>(EMPTY_FILTERS);
  return (
    <GlobalFilters
      scope={SCOPE}
      value={filters}
      onChange={setFilters}
    />
  );
}

test("loads scoped options, applies filters, persists them, and clears them", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockImplementation((input) => String(input).includes("/genres?") ? response({ genres: [
      { content_type: "movie", id: 35, name: "Comedy" },
      { content_type: "movie", id: 18, name: "Drama" },
    ] }) : response({
      content_types: ["movie", "tv"],
      languages: ["el", "en"],
      runtime_minutes: { minimum: 22, maximum: 180 },
      release_year: { minimum: 1990, maximum: 2026 },
      rating: { minimum: 4.5, maximum: 9.1 },
    }));

  render(<Harness />);

  const comedy = await screen.findByRole("button", { name: "Comedy" });
  fireEvent.click(comedy);
  fireEvent.change(screen.getByLabelText("Runtime"), { target: { value: "120" } });
  fireEvent.change(screen.getByLabelText("Minimum rating"), { target: { value: "7" } });
  fireEvent.change(screen.getByLabelText("Language"), { target: { value: "el" } });
  fireEvent.change(screen.getByLabelText("Release year from"), { target: { value: "2020" } });

  expect(comedy).toHaveAttribute("aria-pressed", "true");
  expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual(expect.arrayContaining([
    expect.stringContaining("region=GR&providers=netflix"),
  ]));
  await waitFor(() => expect(JSON.parse(
    localStorage.getItem("watchpulse.discovery-preferences.v1") ?? "{}",
  )).toMatchObject({ genreIds: [35], runtimeMax: 120, ratingMin: 7, language: "el", releaseYearFrom: 2020 }));

  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByLabelText("Runtime")).toHaveValue("");
  expect(comedy).toHaveAttribute("aria-pressed", "false");
});
