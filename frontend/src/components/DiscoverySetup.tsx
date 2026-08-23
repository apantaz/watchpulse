import { useEffect, useState } from "react";
import { getProviders, getRegions, type ProviderOption } from "../api/catalog";
import { loadPreferences, savePreferences } from "../preferences";

type SetupState =
  | { kind: "loading-regions" }
  | { kind: "loading-providers" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

const regionNames = new Intl.DisplayNames([navigator.language], { type: "region" });

export function DiscoverySetup() {
  const saved = loadPreferences();
  const [regions, setRegions] = useState<string[]>([]);
  const [region, setRegion] = useState(saved.region ?? "");
  const [providers, setProviders] = useState<ProviderOption[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>(saved.providers);
  const [state, setState] = useState<SetupState>({ kind: "loading-regions" });

  useEffect(() => {
    const controller = new AbortController();
    getRegions(controller.signal)
      .then((options) => {
        const codes = options.map(({ code }) => code);
        if (codes.length === 0) throw new Error("No regions are available");
        setRegions(codes);
        setRegion((current) => (codes.includes(current) ? current : codes[0]));
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ kind: "error", message: error instanceof Error ? error.message : "Unable to load regions" });
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!region) return;
    const controller = new AbortController();
    setState({ kind: "loading-providers" });
    getProviders(region, controller.signal)
      .then((options) => {
        const validKeys = new Set(options.map(({ key }) => key));
        setProviders(options);
        setSelectedProviders((current) => current.filter((key) => validKeys.has(key)));
        setState({ kind: "ready" });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setState({ kind: "error", message: error instanceof Error ? error.message : "Unable to load services" });
        }
      });
    return () => controller.abort();
  }, [region]);

  useEffect(() => {
    if (state.kind === "ready") savePreferences({ region, providers: selectedProviders });
  }, [region, selectedProviders, state.kind]);

  const toggleProvider = (key: string) => {
    setSelectedProviders((current) =>
      current.includes(key) ? current.filter((value) => value !== key) : [...current, key],
    );
  };

  return (
    <section className="discovery-setup" aria-labelledby="setup-title">
      <div className="setup-heading">
        <div>
          <p className="status-label">Your catalog</p>
          <h2 id="setup-title">Where do you watch?</h2>
        </div>
        {selectedProviders.length > 0 && (
          <span className="selection-count">{selectedProviders.length} selected</span>
        )}
      </div>

      {state.kind === "error" ? (
        <p className="setup-error" role="alert">{state.message}</p>
      ) : (
        <>
          <label className="region-field">
            <span>Region</span>
            <select value={region} onChange={(event) => setRegion(event.target.value)} disabled={!regions.length}>
              {regions.map((code) => (
                <option key={code} value={code}>{regionNames.of(code) ?? code} ({code})</option>
              ))}
            </select>
          </label>

          <fieldset className="provider-fieldset" disabled={state.kind !== "ready"}>
            <legend>Streaming services</legend>
            <div className="provider-grid">
              {providers.map((provider) => {
                const selected = selectedProviders.includes(provider.key);
                return (
                  <button
                    className={`provider-button${selected ? " selected" : ""}`}
                    type="button"
                    aria-pressed={selected}
                    key={provider.key}
                    onClick={() => toggleProvider(provider.key)}
                  >
                    <span className="provider-mark">{provider.name.slice(0, 1)}</span>
                    {provider.name}
                    <span className="check" aria-hidden="true">{selected ? "✓" : "+"}</span>
                  </button>
                );
              })}
            </div>
          </fieldset>
          {state.kind === "loading-regions" && <p className="setup-loading">Loading regions…</p>}
          {state.kind === "loading-providers" && <p className="setup-loading">Loading services…</p>}
        </>
      )}
    </section>
  );
}
