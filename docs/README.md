# WatchPulse Documentation

Each document has one primary responsibility:

- [Architecture](architecture.md): system boundaries, components, and data flow.
- [Data model](data-model.md): grains, keys, fields, history, and data tests.
- [Decisions](decisions.md): append-only architecture decision records (ADRs).
- [Roadmap](roadmap.md): version-by-version scope and exit criteria.
- [Release notes](releases/): completed version outcomes and limitations.

`../AGENTS.md` is the authoritative product brief. When implementation changes a
contract, update the owning document in the same change:

- schema or business semantics → `data-model.md`;
- a meaningful engineering choice → `decisions.md`;
- delivery scope or completion status → `roadmap.md`;
- component boundary or system flow → `architecture.md`.
