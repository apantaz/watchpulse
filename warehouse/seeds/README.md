# Seeds

Small version-controlled reference datasets such as stable provider mappings
and configurable ranking weights. Secrets and source payloads do not belong here.

Seed contracts, column types, ownership, and tests are declared in
`_seeds.yml`. All seeds are built in the dedicated `reference` schema with
unquoted column names, as configured in `dbt_project.yml`.

Current reference datasets:

- `provider_reference.csv`: stable WatchPulse provider keys and names;
- `provider_source_reference.csv`: region-aware upstream provider crosswalks;
- `genre_reference.csv`: TMDB genre names scoped by movie or TV content type.
