{% docs col_first_observed_at %}
Earliest retained observation across the available metadata sources.
{% enddocs %}

{% docs col_metadata_source %}
Source selected for the canonical row; TMDB is preferred when available.
{% enddocs %}

{% docs col_event_effective_at %}
Lifecycle-effective timestamp, using the announced arrival for upcoming events.
{% enddocs %}

{% docs col_available_since %}
Most recent known time the current provider availability began.
{% enddocs %}

{% docs col_is_available %}
Whether the title is part of the current region/provider catalog.
{% enddocs %}

{% docs col_is_upcoming %}
Whether the title is announced for a future or date-unknown arrival.
{% enddocs %}

{% docs col_last_updated_at %}
Latest WatchPulse observation contributing to the availability row.
{% enddocs %}
