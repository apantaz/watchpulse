{% docs col_provider_name %}
Human-readable WatchPulse provider name.
{% enddocs %}

{% docs col_provider_is_active %}
Whether the provider is currently included in WatchPulse serving models.
{% enddocs %}

{% docs col_popularity_score %}
Replaceable discovery ranking input, initially populated from TMDB popularity.
{% enddocs %}

{% docs col_availability_source %}
Source that established the current or upcoming availability state.
{% enddocs %}

{% docs col_catalog_name %}
Stable name of the serving catalog described by the freshness row.
{% enddocs %}

{% docs col_warehouse_built_at %}
Timestamp when dbt built the candidate serving warehouse.
{% enddocs %}

{% docs col_latest_source_updated_at %}
Newest contributing source-observation timestamp in the serving catalog.
{% enddocs %}

{% docs col_catalog_row_count %}
Total number of rows in the serving catalog at build time.
{% enddocs %}

{% docs col_current_row_count %}
Number of currently available rows in the serving catalog at build time.
{% enddocs %}

{% docs col_upcoming_row_count %}
Number of upcoming rows in the serving catalog at build time.
{% enddocs %}

{% docs col_genre_id %}
TMDB genre identifier scoped by content type.
{% enddocs %}

{% docs col_genre_name %}
Normalized user-facing genre name.
{% enddocs %}

{% docs col_source_provider_id %}
Provider identifier used by the named upstream source.
{% enddocs %}

{% docs col_created_at %}
Timestamp of the earliest retained metadata observation for the content.
{% enddocs %}

{% docs col_updated_at %}
Timestamp of the latest retained metadata observation selected for the content.
{% enddocs %}
