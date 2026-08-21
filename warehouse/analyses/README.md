# Analyses

Read-only analytical SQL that compiles through dbt but is not materialized by
`dbt build`. Analyses may reference documented models with `ref()` and must not
become hidden serving dependencies.
