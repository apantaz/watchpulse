import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { DiscoverySetup } from "./DiscoverySetup";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

const jsonResponse = (value: unknown) =>
  Promise.resolve(new Response(JSON.stringify(value), { status: 200 }));

test("loads region-aware providers and persists the guest selection", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => jsonResponse({ regions: [{ code: "GR" }, { code: "US" }] }))
    .mockImplementationOnce(() => jsonResponse({ region: "GR", providers: [
      { key: "netflix", name: "Netflix" },
      { key: "disney_plus", name: "Disney+" },
    ] }));

  render(<DiscoverySetup onScopeChange={vi.fn()} />);

  const netflix = await screen.findByRole("button", { name: /Netflix/ });
  fireEvent.click(netflix);

  expect(netflix).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByText("1 selected")).toBeInTheDocument();
  await waitFor(() => expect(localStorage.getItem("watchpulse.discovery-preferences.v1")).toContain("netflix"));
  expect(fetchMock.mock.calls[1][0]).toContain("/api/v1/catalog/providers?region=GR");
});

test("changing region reloads providers and removes an invalid selection", async () => {
  localStorage.setItem(
    "watchpulse.discovery-preferences.v1",
    JSON.stringify({ region: "GR", providers: ["netflix"] }),
  );
  vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => jsonResponse({ regions: [{ code: "GR" }, { code: "US" }] }))
    .mockImplementationOnce(() => jsonResponse({ region: "GR", providers: [{ key: "netflix", name: "Netflix" }] }))
    .mockImplementationOnce(() => jsonResponse({ region: "US", providers: [{ key: "hulu", name: "Hulu" }] }));

  render(<DiscoverySetup onScopeChange={vi.fn()} />);
  expect(await screen.findByRole("button", { name: /Netflix/ })).toHaveAttribute("aria-pressed", "true");
  fireEvent.change(screen.getByLabelText("Region"), { target: { value: "US" } });

  expect(await screen.findByRole("button", { name: /Hulu/ })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Netflix/ })).not.toBeInTheDocument();
  await waitFor(() => expect(JSON.parse(
    localStorage.getItem("watchpulse.discovery-preferences.v1") ?? "{}",
  )).toMatchObject({ region: "US", providers: [] }));
});
