{% docs col_tmdb_id %}
Canonical TMDB content identifier.
{% enddocs %}

{% docs col_content_type %}
Internal content type: `movie` or `tv`.
{% enddocs %}

{% docs col_region %}
Uppercase ISO 3166-1 alpha-2 availability region.
{% enddocs %}

{% docs col_provider_key %}
Stable WatchPulse provider identifier.
{% enddocs %}

{% docs col_title %}
User-facing movie title or TV series name.
{% enddocs %}

{% docs col_original_title %}
Title in the content's original language when supplied by TMDB.
{% enddocs %}

{% docs col_overview %}
TMDB synopsis; nullable when no overview is available.
{% enddocs %}

{% docs col_release_date %}
Movie release date or TV first-air date.
{% enddocs %}

{% docs col_release_year %}
Four-digit content release year when the source does not provide a full date.
{% enddocs %}

{% docs col_runtime_minutes %}
Content runtime in minutes when supplied by the selected metadata source.
{% enddocs %}

{% docs col_genre_ids %}
JSON array of TMDB genre identifiers awaiting normalization.
{% enddocs %}

{% docs col_source_genres %}
Unmodified Streaming Availability genre objects retained for future mapping.
{% enddocs %}

{% docs col_original_language %}
TMDB original-language code.
{% enddocs %}

{% docs col_tmdb_rating %}
TMDB vote average on the zero-to-ten scale.
{% enddocs %}

{% docs col_vote_count %}
Number of TMDB votes contributing to the rating.
{% enddocs %}

{% docs col_tmdb_popularity %}
TMDB popularity value at discovery time.
{% enddocs %}

{% docs col_poster_path %}
Relative TMDB poster image path.
{% enddocs %}

{% docs col_backdrop_path %}
Relative TMDB backdrop image path.
{% enddocs %}

{% docs col_source_updated_at %}
Timestamp when WatchPulse fetched the selected source observation.
{% enddocs %}

{% docs col_source_file %}
Local Parquet file retained for lineage and deterministic tie-breaking.
{% enddocs %}

{% docs col_event_id %}
Deterministic WatchPulse lifecycle event identifier.
{% enddocs %}

{% docs col_monetization_type %}
Commercial availability type, such as subscription, rent, or buy.
{% enddocs %}

{% docs col_event_type %}
Lifecycle transition reported by the upstream source.
{% enddocs %}

{% docs col_event_date %}
Effective lifecycle timestamp when supplied by the upstream source.
{% enddocs %}

{% docs col_available_from %}
Announced future availability timestamp for an upcoming event.
{% enddocs %}

{% docs col_expires_on %}
Announced expiration timestamp for an expiring event.
{% enddocs %}

{% docs col_source %}
Source adapter that produced the normalized event.
{% enddocs %}

{% docs col_source_event_id %}
Nullable upstream event identifier when one exists.
{% enddocs %}

{% docs col_ingested_at %}
Timestamp when WatchPulse normalized and persisted the event.
{% enddocs %}
