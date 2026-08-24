import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => vi.restoreAllMocks());

test("shows catalog readiness returned by the local API", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      catalog_name: "catalog_availability",
      warehouse_built_at: "2026-08-23T10:00:00",
      latest_source_updated_at: "2026-08-23T09:00:00",
      catalog_row_count: 190,
      current_row_count: 160,
      upcoming_row_count: 30
    }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ regions: [{ code: "GR" }] }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({
      region: "GR",
      providers: [{ key: "netflix", name: "Netflix" }]
    }), { status: 200 }));

  render(<App />);
  expect(screen.getByText("Connecting to WatchPulse…")).toBeInTheDocument();
  expect(await screen.findByText(/Updated/)).toBeInTheDocument();
  expect(await screen.findByRole("button", { name: /Netflix/ })).toBeInTheDocument();
});

test("shows an honest error when the catalog is unavailable", async () => {
  vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "missing" }), { status: 503 }));
  render(<App />);
  await waitFor(() => expect(screen.getByText("Catalog is not published yet")).toBeInTheDocument());
});
