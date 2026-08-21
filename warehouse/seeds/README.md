# Seeds

Small version-controlled reference datasets such as stable provider mappings
and configurable ranking weights. Secrets and source payloads do not belong here.

Seed contracts, column types, ownership, and tests are declared in
`_seeds.yml`. All seeds are built in the dedicated `reference` schema with
unquoted column names, as configured in `dbt_project.yml`.
